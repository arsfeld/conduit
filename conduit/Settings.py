"""
Stores application settings

Part of this code copied from Gimmie (c) Alex Gravely

Copyright: John Stowers, 2006
License: GPLv2
"""
import gobject

try:
    import gconf
except ImportError:
    from gnome import gconf

import logging
log = logging.getLogger("Settings")

#import gnomekeyring
#import conduit

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
    "bool"      :   lambda x: string_to_bool(x),
    "string"    :   lambda x: str(x),
    "list"      :   lambda x: string_to_list(x)
}
TYPE_TO_STRING = {
    int     :   lambda x: str(x),
    bool    :   lambda x: str(x),
    str     :   lambda x: str(x),
    list    :   lambda x: list_to_string(x)
}

def string_to_bool(stringy):
    #Because bool("False") doesnt work as expected when restoring strings
    if stringy == "True":
        return True
    else:
        return False
    
def list_to_string(listy):
    s = ""
    if type(listy) is list:
        s = ",".join(listy) #cool
    return s
    
def string_to_list(string, listInternalVtype=str):
    l = string.split(",")
    internalTypeName = TYPE_TO_TYPE_NAME[listInternalVtype]
    for i in range(0, len(l)):
        l[i] = STRING_TO_TYPE[internalTypeName](l[i])
    return l

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
        'show_splashscreen'         :   True,           #The splashscreen can be quite useful on slow computers
        'show_dp_description'       :   False,          #Should the treeview show the dataprovider description
        'show_status_icon'          :   True,           #Show an icon in the notification area indicating if a sync is running
        'save_on_exit'              :   True,           #Is the sync set saved on exit automatically?
        'enable_network'            :   True,           #Should conduit look for other conduits on the local network
        'enable_removable_devices'  :   True,           #Should conduit support iPods, USB keys, etc
        'default_policy_conflict'   :   "ask",          #Default conflict policy for new Conduits, ask,replace,skip
        'default_policy_deleted'    :   "ask",          #Default deleted policy for new Conduits, ask,replace,skip
        'gui_expanded_columns'      :   [],             #list of expanded column paths in the treeview
        'gui_hpane_postion'         :   250,            #The hpane seperating the canvas and treeview position
        'gui_window_size'           :   [],             #W,H
        'gui_minimize_to_tray'      :   False,          #Behaviour when one minimizes the main window, should it iconify?
        'gui_initial_canvas_height' :   450,            #Reduce to ~300 for eepc, etc
        'gui_initial_canvas_width'  :   450,            #Reduce for eepc, etc
        'web_login_browser'         :   "gtkmozembed"   #When loggin into websites use: "system","gtkmozembed","webkit","gtkhtml"
    }
    CONDUIT_GCONF_DIR = "/apps/conduit/"
        
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
        elif vtype in [list, tuple]:
            return value.get_list()
            
        log.warn("Unknown gconf key: %s" % key)
        return None

    def set(self, key, value, vtype=None):
        """
        Sets the key value in gconf and connects adds a signal 
        which is fired if the key changes
        """
        log.debug("Settings %s -> %s" % (key, value))
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
        elif vtype in [list, tuple]:
            #Save every value as a string
            strvalues = [str(i) for i in value]
            self.client.set_list(key, gconf.VALUE_STRING, strvalues)
        else:
            log.warn("Unknown gconf type (k:%s v:%s t:%s)" % (key,value,vtype))
            return False

        return True            
        

