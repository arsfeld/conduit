"""
Stores application settings

Part of this code copied from Gimmie (c) Alex Gravely

Copyright: John Stowers, 2006
License: GPLv2
"""

import os, os.path
import gobject
import gconf
import traceback
#import gnomekeyring

from conduit import log,logd,logw

class Settings(gobject.GObject):
    """
    Class for storing conduit.GLOBALS.settings. 
    
    Settings come in two categories.
    1) Preferences which are application specific and get stored in gconf
    2) Per conduit.GLOBALS.settings.which describe the way dataproviders are connected
    and the specific per dataprovider sync settings.
    
    Keys of type str, bool, int, and list of strings supported at this stage
    """
    __gsignals__ = {
        'changed' : (gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_DETAILED, gobject.TYPE_NONE, ()),
    }

    #Default values for conduit settings
    DEFAULTS = {
        'show_splashscreen'         :   True,       #The splashscreen can be quite useful on slow computers
        'show_dp_description'       :   False,      #Should the treeview show the dataprovider description
        'show_status_icon'          :   True,       #Show an icon in the notification area indicating if a sync is running
        'save_on_exit'              :   False,      #Is the sync set saved on exit automatically?
        'enable_network'            :   True,       #Should conduit look for other conduits on the local network
        'enable_removable_devices'  :   True,       #Should conduit support iPods, USB keys, etc
        'twoway_policy_conflict'    :   "ask",      #ask,replace,skip
        'twoway_policy_deleted'     :   "ask",      #ask,replace,skip
        'gui_expanded_columns'      :   [],         #list of expanded column paths in the treeview
        'gui_hpane_postion'         :   250,        #The hpane seperating the canvas and treeview position
        'gui_window_size'           :   [],         #W,H
        'gui_minimize_to_tray'      :   False,      #Behaviour when one minimizes the main window, should it iconify?
        'web_login_browser'         :   "system"    #When loggin into websites use: "system","gtkmozembed","webkit","gtkhtml"
    }
    CONDUIT_GCONF_DIR = "/apps/conduit/"
    #these dicts are used for mapping config setting types to type names
    #and back again (isnt python cool...)
    TYPE_TO_TYPE_NAME = {
        int     :   "int",
        bool    :   "bool",
        str     :   "string",
        list    :   "list"
    }
    STRING_TO_TYPE = {
        "int"       :   lambda x: int(x),
        "bool"      :   lambda x: Settings._string_to_bool(x),
        "string"    :   lambda x: str(x),
        "list"      :   lambda x: Settings._string_to_list(x)
    }
    TYPE_TO_STRING = {
        int     :   lambda x: str(x),
        bool    :   lambda x: str(x),
        str     :   lambda x: str(x),
        list    :   lambda x: Settings._list_to_string(x)
    }
        
    def __init__(self):
        """
        @param xmlSettingFilePath: The path to the xml file in which to store
        the per-conduit settings
        @type xmlSettingFilePath: C{string}
        """
        gobject.GObject.__init__(self)
        self.client = gconf.client_get_default()
        # Preload gconf directories
        self.client.add_dir(self.CONDUIT_GCONF_DIR[:-1], gconf.CLIENT_PRELOAD_RECURSIVE)  
        self.notifications = []

        # Init the keyring
        self.classUsernamesAndPasswords = {}

        #FIXME: BROKEN
        #http://bugzilla.gnome.org/show_bug.cgi?id=376183
        #http://bugzilla.gnome.org/show_bug.cgi?id=363019
        #self._init_keyring()

    @staticmethod
    def _string_to_bool(stringy):
        #Because bool("False") doesnt work as expected when restoring strings
        if stringy == "True":
            return True
        else:
            return False
        
    @staticmethod    
    def _list_to_string(listy):
        s = ""
        if type(listy) is list:
            s = ",".join(listy) #cool
        return s
        
    @staticmethod
    def _string_to_list(string, listInternalVtype=str):
        l = string.split(",")
        internalTypeName = Settings.TYPE_TO_TYPE_NAME[listInternalVtype]
        for i in range(0, len(l)):
            l[i] = Settings.STRING_TO_TYPE[internalTypeName](l[i])
        return l

    def _init_keyring(self):
        """
        Connects to the Gnome Keyring. All passwords are stored under a 
        conduit key, in the format

        classname:username:password;classname:username:password

        This function gets all the usernames and passwords and puts them in a
        dict organised by class name
        """
        pass
        #self.keyring = gnomekeyring.get_default_keyring_sync()
        #token = self.get("%s_token" % conduit.APPNAME, int, 0)
        #if token > 0:
        #    secrets = gnomekeyring.item_get_info_sync(self.keyring, token).get_secret()
        #    for i in secrets.split(';'):
        #        j = i.split(':')
        #        self.classUsernamesAndPasswords[j[0]] = (j[0], j[1])

    def _fix_key(self, key):
        """
        Appends the CONDUIT_GCONF_PREFIX to the key if needed
        
        @param key: The key to check
        @type key: C{string}
        @returns: The fixed key
        @rtype: C{string}
        """
        if not key.startswith(self.CONDUIT_GCONF_DIR):
            return self.CONDUIT_GCONF_DIR + key
        else:
            return key
            
    def _key_changed(self, client, cnxn_id, entry, data=None):
        """
        Callback when a gconf key changes
        """
        key = self._fix_key(entry.key)
        detailed_signal = 'changed::%s' % key
        self.emit(detailed_signal)

    def get(self, key, vtype=None, default=None):
        """
        Returns the value of the key or the default value if the key is 
        not yet in gconf
        """
        if key in self.DEFAULTS:
            #function arguments override defaults
            if default is None:
                default = self.DEFAULTS[key]
            if vtype is None:
                vtype = type(default)

        #for gconf refer to the full key path
        key = self._fix_key(key)

        if key not in self.notifications:
            self.client.notify_add(key, self._key_changed)
            self.notifications.append(key)
        
        value = self.client.get(key)
        if not value:
            self.set(key, default, vtype)
            return default

        if vtype is bool:
            return value.get_bool()
        elif vtype is str:
            return value.get_string()
        elif vtype is int:
            return value.get_int()
        elif vtype is list:
            return value.get_list()

    def set(self, key, value, vtype=None):
        """
        Sets the key value in gconf and connects adds a signal 
        which is fired if the key changes
        """
        if key in self.DEFAULTS and not vtype:
            vtype = type(self.DEFAULTS[key])

        #for gconf refer to the full key path
        key = self._fix_key(key)

        if vtype is bool:
            self.client.set_bool(key, value)
        elif vtype is str:
            self.client.set_string(key, value)
        elif vtype is int:
            self.client.set_int(key, value)
        elif vtype is list:
            #Save every value as a string
            strvalues = [str(i) for i in value]
            self.client.set_list(key, gconf.VALUE_STRING, strvalues)
        else:
            logw("Unknown gconf type (k:%s v:%s t:%s)" % (key,value,vtype))

    def get_username_and_password(self, classname):
        """
        Returns a tuple of username and password for the class defined
        by classname
        """
        pass
    
    def set_username_and_password(self, classname, password, username=''):
        """
        Stores the username and password for the class called classname
        """        
        pass


