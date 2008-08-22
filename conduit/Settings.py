"""
Stores application settings

Part of this code copied from Gimmie (c) Alex Gravely

Copyright: John Stowers, 2006
License: GPLv2
"""
import gobject

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
    Class for storing conduit.GLOBALS.settings. Keys of type str, bool, int, 
    and list of strings supported at this stage.
    
    Also stores the special proxy settings.
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
        'gui_expanded_rows'         :   [],             #list of expanded column paths in the treeview
        'gui_restore_expanded_rows' :   True,           #Shoud we expand columns at startup
        'gui_hpane_postion'         :   250,            #The hpane seperating the canvas and treeview position
        'gui_window_size'           :   [],             #W,H
        'gui_minimize_to_tray'      :   False,          #Behaviour when one minimizes the main window, should it iconify?
        'gui_initial_canvas_height' :   450,            #Reduce to ~300 for eepc, etc
        'gui_initial_canvas_width'  :   450,            #Reduce for eepc, etc
        'gui_use_rgba_colormap'     :   False,          #Seems to corrupt gtkmozembed on some systems
        'gui_show_hints'            :   True,           #Show message area hints in the Conduit GUI
        'gui_show_treeview_lines'   :   False,          #Show treeview lines
    }
        
    def __init__(self, implName):
        gobject.GObject.__init__(self)
        if implName == "GConf":
            from conduit.platform.SettingsGConf import SettingsImpl            
        else:
            from conduit.platform.SettingsPython import SettingsImpl

        self._impl = SettingsImpl(
                        defaults=self.DEFAULTS,
                        changedCb=self._key_changed)
        
    def _key_changed(self, key):
        self.emit('changed::%s' % key)
        
    def set_overrides(self, **overrides):
        """
        Sets values of settings that only exist for this setting, and are
        never saved, nor updated.
        """
        self._impl.set_overrides(**overrides)

    def get(self, key, **kwargs):
        """
        Returns the value of the key or the default value if the key is 
        not yet stored
        """
        return self._impl.get(key, **kwargs)

    def set(self, key, value, **kwargs):
        """
        Sets the key to value.
        """
        return self._impl.set(key, value, **kwargs)
        
    def proxy_enabled(self):
        """
        @returns: True if the user has specified a http proxy via
        the http_proxy environment variable, or in the appropriate settings
        backend, such as gconf
        """
        return self._impl.proxy_enabled()
        
    def get_proxy(self):
        """
        Returns the details of the configured http proxy. 
        The http_proxy environment variable overrides the GNOME setting
        @returns: host,port,user,password
        """
        return self._impl.get_proxy()

    def save(self):
        """
        Performs any necessary tasks to ensure settings are saved between sessions
        """
        self._impl.save()


