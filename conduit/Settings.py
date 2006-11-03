"""
Stores application settings

Part of this code copied from Gimmie (c) Alex Gravely

Copyright: John Stowers, 2006
License: GPLv2
"""

import os
import os.path
import gobject
import gconf
import traceback
import xml.dom.ext
from xml.dom import minidom
from xml.dom.minidom import Document
import gnomekeyring

import conduit
import logging

class Settings(gobject.GObject):
    """
    Class for storing conduit settings. 
    
    Settings come in two categories.
    1) Preferences which are application specific and get stored in gconf
    2) Per conduit settings which describe the way dataproviders are connected
    and the specific per dataprovider sync settings.
    
    Keys of type str and bool supported at this stage
    """
    __gsignals__ = {
        'changed' : (gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_DETAILED, gobject.TYPE_NONE, ()),
    }

    #Default values for conduit settings
    DEFAULTS = {
        'show_splashscreen' :   True,   #The splashscreen can be quite useful on slow computers
        'use_treeview'      :   False,  #Arrange the dataproviders in a treeview (or a listview)
        'save_on_exit'      :   False   #Is the sync set saved on exit automatically?
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
        
    def __init__(self, xmlSettingFilePath="settings.xml"):
        """
        @param xmlSettingFilePath: The path to the xml file in which to store
        the per-conduit settings
        @type xmlSettingFilePath: C{string}
        """
        gobject.GObject.__init__(self)
        self.client = gconf.client_get_default()
        # Preload gconf directories
        self.client.add_dir(self.CONDUIT_GCONF_DIR[:-1], gconf.CLIENT_PRELOAD_RECURSIVE)  
        self.xmlSettingFilePath = xmlSettingFilePath
        self.notifications = []

        # Init the keyring
        self.classUsernamesAndPasswords = {}
        self._init_keyring()

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

        self.keyring = gnomekeyring.get_default_keyring_sync()
        token = self.get("%s_token" % conduit.APPNAME, int, 0)
        if token > 0:
            secrets = gnomekeyring.item_get_info_sync(self.keyring, token).get_secret()
            for i in secrets.split(';'):
                j = i.split(':')
                self.classUsernamesAndPasswords[j[0]] = (j[0], j[1])

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

    def set_settings_file(self, xmlSettingFilePath):
        """
        Sets the xml settings file to be used in the restore_sync_set
        and save_sync_set methods
        @param xmlSettingFilePath: Full locl path to the settings.xml file
        """
        logging.debug("Settings stored in %s" % xmlSettingFilePath)
        self.xmlSettingFilePath = xmlSettingFilePath
        
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
            self.set(key, vtype, default)
            return default

        if vtype is bool:
            return value.get_bool()
        elif vtype is str:
            return value.get_string()
        elif vtype is int:
            return value.get_int()

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

    def save_sync_set(self, version, syncSet):
        """
        Saves the synchronisation settings (icluding all dataproviders and how
        they are connected) to an xml file so that the 'sync set' can
        be restored later
        
        @param version: The version of the saved settings xml file. Necessary
        when conduit is updated and the xml format may change.
        @type version: C{string}
        @param syncSet: A list of conduits to save
        @type syncSet: L{conduit.Conduit.Conduit}[]
        """
        def make_xml_configuration(parentNode, configDict):
            for config in configDict:
                    configxml = doc.createElement(str(config))
                    #store the value and value type
                    try:
                        vtype = Settings.TYPE_TO_TYPE_NAME[ type(configDict[config]) ]
                        value = Settings.TYPE_TO_STRING[  type(configDict[config]) ](configDict[config])
                    except KeyError:
                        logging.warn("Cannot convert %s to string. Value of %s not saved" % (type(value), config))
                        vtype = Settings.TYPE_TO_TYPE_NAME[str]
                        value = Settings.TYPE_TO_STRING[str](configDict[config])
                    configxml.setAttribute("type", vtype)
                    configxml.appendChild(doc.createTextNode(value))
                    parentNode.appendChild(configxml)    
            
        logging.info("Saving Sync Set")
        #Build the application settings xml document
        doc = Document()
        rootxml = doc.createElement("conduit-application")
        rootxml.setAttribute("version", version)
        doc.appendChild(rootxml)
        
        #Store the conduits
        for conduit in syncSet:
            conduitxml = doc.createElement("conduit")
            #First store conduit specific settings
            x,y,w,h = conduit.get_conduit_dimensions()
            conduitxml.setAttribute("x",str(x))
            conduitxml.setAttribute("y",str(y))
            conduitxml.setAttribute("w",str(w))
            conduitxml.setAttribute("h",str(h))
            rootxml.appendChild(conduitxml)
            
            #Store the source
            source = conduit.datasource
            if source is not None:
                sourcexml = doc.createElement("datasource")
                sourcexml.setAttribute("classname", source.classname)
                conduitxml.appendChild(sourcexml)
                #Store source settings
                configurations = source.module.get_configuration()
                #logging.debug("Source Settings %s" % configurations)
                make_xml_configuration(sourcexml, configurations)
            
            #Store all sinks
            sinksxml = doc.createElement("datasinks")
            for sink in conduit.datasinks:
                sinkxml = doc.createElement("datasink")
                sinkxml.setAttribute("classname", sink.classname)
                sinksxml.appendChild(sinkxml)
                #Store sink settings
                configurations = sink.module.get_configuration()
                #logging.debug("Sink Settings %s" % configurations)
                make_xml_configuration(sinkxml, configurations)
            conduitxml.appendChild(sinksxml)        

        #Save to disk
        try:
            file_object = open(self.xmlSettingFilePath, "w")
            xml.dom.ext.PrettyPrint(doc, file_object)
            file_object.close()        
        except IOError, err:
            logging.critical("Could not save settings to %s (Error: %s)" % (self.xmlSettingFilePath, err.strerror))
        
    def restore_sync_set(self, expectedVersion, mainWindow):
        """
        Restores sync settings from the xml file
        
        SORRY ABOUT THE UGLYNESS AND COMPLETE LACK OF ROBUSTNESS
        """
        logging.info("Restoring Sync Set")
        def get_settings(xml):
            """
            Makes a dict of dataprovider settings (settings are child nodes
            of dataproviders and in the form <settingname>value</settingname>
            """
            settings = {}
            for s in xml.childNodes:
                if s.nodeType == s.ELEMENT_NODE:
                    #now convert the setting to the correct type
                    raw = s.childNodes[0].data
                    vtype = s.getAttribute("type")
                    try:
                        data = Settings.STRING_TO_TYPE[vtype](raw)
                    except KeyError:
                        #fallback to string type
                        logging.warn("Cannot convert string (%s) to native type %s" % (raw, vtype))
                        traceback.print_exc()
                        data = str(raw)
                    logging.debug("Read Setting: Name=%s Value=%s Type=%s" % (s.localName, data, type(data)))
                    settings[s.localName] = data
            return settings
            
        def restore_dataprovider(dpClassname, dpSettings, x, y):
            """
            Adds the dataprovider back onto the canvas at the specifed
            location and configures it with the given settings
            """
            #logging.debug("Restoring %s to (x=%s,y=%s)" % (dpClassname,x,y))
            dpWrapper = mainWindow.modules.get_new_instance_module_named(dpClassname)
            if dpWrapper is not None:
                dpWrapper.module.set_configuration(dpSettings)
                mainWindow.canvas.add_dataprovider_to_canvas(dpWrapper, x, y)
            else:
                logging.warn("Could not restore %s to (x=%s,y=%s)" % (dpClassname,x,y))
            

        #Check the file exists
        if not os.path.isfile(self.xmlSettingFilePath):
            logging.info("%s not present" % self.xmlSettingFilePath)
            return
            
        try:
            #Open                
            doc = minidom.parse(self.xmlSettingFilePath)
            xmlVersion = doc.getElementsByTagName("conduit-application")[0].getAttribute("version")
            #And check it is the correct version        
            if expectedVersion != xmlVersion:
                logging.info("%s xml file is incorrect version" % self.xmlSettingFilePath)
                os.remove(self.xmlSettingFilePath)
                return
            
            #Parse...    
            for conds in doc.getElementsByTagName("conduit"):
                x = conds.getAttribute("x")
                y = conds.getAttribute("y")
                #each conduit
                for i in conds.childNodes:
                    #one datasource
                    if i.nodeType == i.ELEMENT_NODE and i.localName == "datasource":
                        classname = i.getAttribute("classname")
                        settings = get_settings(i)
                        #add to canvas
                        if len(classname) > 0:
                            restore_dataprovider(classname,settings,x,y)
                    #many datasinks
                    elif i.nodeType == i.ELEMENT_NODE and i.localName == "datasinks":
                        #each datasink
                        for sink in i.childNodes:
                            if sink.nodeType == sink.ELEMENT_NODE and sink.localName == "datasink":
                                classname = sink.getAttribute("classname")
                                settings = get_settings(sink)
                                #add to canvas
                                if len(classname) > 0:
                                    restore_dataprovider(classname,settings,x,y)                        

        #FIXME: Should i special case different exceptions here....?
        except:
            logging.warn("Error parsing %s. Exception:\n%s" % (self.xmlSettingFilePath, traceback.format_exc()))
            os.remove(self.xmlSettingFilePath)
