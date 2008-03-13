"""
Cotains classes for representing DataSources or DataSinks.

Copyright: John Stowers, 2006
License: GPLv2
"""
import xml.dom.minidom
import traceback
import gobject
from gettext import gettext as _
import logging
log = logging.getLogger("dataproviders.DataProvider")

import conduit
import conduit.ModuleWrapper as ModuleWrapper
import conduit.Utils as Utils
import conduit.Settings as Settings

#Constants used in the sync state machine
STATUS_NONE = 0
STATUS_CHANGE_DETECTED = 1
STATUS_REFRESH = 2
STATUS_DONE_REFRESH_OK = 3
STATUS_DONE_REFRESH_ERROR = 4
STATUS_SYNC = 5
STATUS_DONE_SYNC_OK = 6
STATUS_DONE_SYNC_ERROR = 7
STATUS_DONE_SYNC_SKIPPED = 8
STATUS_DONE_SYNC_CANCELLED = 9
STATUS_DONE_SYNC_CONFLICT = 10
STATUS_DONE_SYNC_NOT_CONFIGURED = 11


class DataProviderBase(gobject.GObject):
    """
    Model of a DataProvider. Can be a source or a sink
    """
    
    __gsignals__ =  { 
                    "status-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "change-detected": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }
                    
    _name_ = ""
    _description_ = ""
    _icon_ = ""
    _module_type_ = "dataprovider"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _out_type_ = ""
    _in_type_ = ""
    
    def __init__(self, *args):
        """
        All sync functionality should be provided by derived classes
        """
        gobject.GObject.__init__(self)

        self.pendingChangeDetected = False
        self.icon = None
        self.status = STATUS_NONE

    def __emit_status_changed(self):
        """
        Emits a 'status-changed' signal to the main loop.
        
        You should connect to this signal if you wish to be notified when
        the derived DataProvider goes through its stages (STATUS_* etc)
        """
        self.emit("status-changed")
        return False

    def __emit_change_detected(self):
        """
        Emits a 'change-detected' signal to the main loop.
        """
        log.debug("Change detected in dataproviders data (%s)" % self.get_UID())

        self.set_status(STATUS_CHANGE_DETECTED)
        self.emit("change-detected")
        self.pendingChangeDetected = False

    def emit(self, *args):
        """
        Override the gobject signal emission so that all signals are emitted 
        from the main loop on an idle handler
        """
        gobject.idle_add(gobject.GObject.emit,self,*args)
        
    def initialize(self):
        """
        Called when the module is loaded by the module loader. 
        
        It is called in the main thread so should NOT block. It should perform
        simple tests to determine whether the dataprovider is applicable to 
        the user and whether is should be presented to them. For example it
        may check if a specific piece of hardware is loaded, or check if
        a user has the specific piece of software installed with which
        it synchronizes.
        
        @returns: True if the module initialized correctly (is appropriate
        for the user), False otherwise
        @rtype: C{bool}
        """
        return True

    def uninitialize(self):
        """
        Called just before the application quits.
        """
        pass
        
    def refresh(self):
        """
        Performs any (conduit.logging in, etc) which must be undertaken on the 
        dataprovider prior to calling get_all(). Should gather all information
        so a subsequent call to get_all() can return the uids of all the
        data this dataprovider holds
        
        This function may be called multiple times so derived classes should
        be aware of this.

        Derived classes should call this function to ensure the dataprovider
        status is updated.
        """
        self.set_status(STATUS_REFRESH)

    def finish(self, *args):
        """
        Perform any post-sync cleanup. For example, free any structures created
        in refresh that were used in the synchronization.
        """
        if self.pendingChangeDetected:
            self.__emit_change_detected()

    def emit_change_detected(self):
        if self.is_busy():
            self.pendingChangeDetected = True
        else:
            self.__emit_change_detected()

    def set_status(self, newStatus):
        """
        Sets the dataprovider status. If the status has changed then emits
        a status-changed signal
        
        @param newStatus: The new status
        @type newStatus: C{int}
        """
        if newStatus != self.get_status():
            self.status = newStatus
            self.__emit_status_changed()
        
    def get_status(self):
        """
        @returns: The current dataproviders status (code)
        @rtype: C{int}
        """
        return self.status
        
    def get_status_text(self):
        """
        @returns: a textual representation of the current dataprover status
        @rtype: C{str}
        """
        s = self.get_status()
        if s == STATUS_NONE:
            return _("Ready")
        elif s == STATUS_CHANGE_DETECTED:
            return _("New data to sync")
        elif s == STATUS_REFRESH:
            return _("Refreshing...")
        elif s == STATUS_DONE_REFRESH_OK:
            return _("Refreshed OK")
        elif s == STATUS_DONE_REFRESH_ERROR:
            return _("Error Refreshing")
        elif s == STATUS_SYNC:
            return _("Synchronizing...")
        elif s == STATUS_DONE_SYNC_OK:
            return _("Synchronized OK")
        elif s == STATUS_DONE_SYNC_ERROR:
            return _("Error Synchronizing")
        elif s == STATUS_DONE_SYNC_SKIPPED:
            return _("Synchronization Skipped")
        elif s == STATUS_DONE_SYNC_CANCELLED:
            return _("Synchronization Cancelled")
        elif s == STATUS_DONE_SYNC_CONFLICT:
            return _("Synchronization Conflict")
        elif s == STATUS_DONE_SYNC_NOT_CONFIGURED:
            return _("Not Configured Correctly")
        else:
            return "BAD PROGRAMMER"
            
    def is_busy(self):
        """
        A DataProvider is busy if it is currently in the middle of the
        intialization or synchronization process.
        
        @todo: This simple test introduces a few (many) corner cases where 
        the function will return the wrong result. Think about this harder
        """
        s = self.get_status()
        if s == STATUS_REFRESH:
            return True
        elif s == STATUS_SYNC:
            return True
        else:
            return False

    def configure(self, window):
        """
        Show a configuration box for configuring the dataprovider instance.
        @param window: The parent gtk.Window (to show a modal dialog)
        """
        log.debug("configure() not overridden by derived class %s" % self._name_)

    def is_configured(self, isSource, isTwoWay):
        """
        Checks if the dp has been configured or not (and if it needs to be)
        @param isSource: True if the dataprovider is in the source position
        @param isTwoway: True if the dataprovider is a member of a two-way sync
        """
        return True
        
    def get_configuration(self):
        """
        Returns a dictionary of strings to be saved, representing the dataproviders
        current configuration. Should be overridden by all dataproviders wishing
        to be able to save their state between application runs
        @returns: Dictionary of strings containing application settings
        @rtype: C{dict(string)}
        """
        log.debug("get_configuration() not overridden by derived class %s" % self._name_)
        return {}

    def get_configuration_xml(self):
        """
        Returns the dataprovider configuration as xml
        @rtype: C{string}
        """
        doc = xml.dom.minidom.Element("configuration")
        configDict = self.get_configuration()
        for config in configDict:
                configxml = xml.dom.minidom.Element(str(config))
                #store the value and value type
                try:
                    vtype = Settings.TYPE_TO_TYPE_NAME[ type(configDict[config]) ]
                    value = Settings.TYPE_TO_STRING[  type(configDict[config]) ](configDict[config])
                except KeyError:
                    log.warn("Cannot convert %s to string. Value of %s not saved" % (type(value), config))
                    vtype = Settings.TYPE_TO_TYPE_NAME[str]
                    value = Settings.TYPE_TO_STRING[str](configDict[config])
                configxml.setAttribute("type", vtype)
                valueNode = xml.dom.minidom.Text()
                valueNode.data = value
                configxml.appendChild(valueNode)
                doc.appendChild(configxml)

        return doc.toxml()

    def set_configuration(self, config):
        """
        Restores applications settings
        @param config: dictionary of dataprovider settings to restore
        """
        log.debug("set_configuration() not overridden by derived class %s" % self._name_)
        for c in config:
            #Perform these checks to stop malformed xml from stomping on
            #unintended variables or posing a security risk by overwriting methods
            if getattr(self, c, None) != None and callable(getattr(self, c, None)) == False:
                log.debug("Setting %s to %s" % (c, config[c]))
                setattr(self,c,config[c])
            else:
                log.warn("Not restoring %s setting: Exists=%s Callable=%s" % (
                    c,
                    getattr(self, c, False),
                    callable(getattr(self, c, None)))
                    )

    def set_configuration_xml(self, xmltext):
        """
        Restores applications settings from XML

        @param xmltext: xml representation of settings
        @type xmltext: C{string}
        """
        doc = xml.dom.minidom.parseString(xmltext)
        configxml = doc.documentElement

        if configxml.nodeType == configxml.ELEMENT_NODE and configxml.localName == "configuration":
            settings = {}
            for s in configxml.childNodes:
                if s.nodeType == s.ELEMENT_NODE:
                    #now convert the setting to the correct type (if filled out)
                    if s.hasChildNodes():
                        raw = s.firstChild.data
                        vtype = s.getAttribute("type")
                        try:
                            data = Settings.STRING_TO_TYPE[vtype](raw)
                        except KeyError:
                            #fallback to string type
                            log.warn("Cannot convert string (%s) to native type %s\n" % (raw, vtype, traceback.format_exc()))
                            data = str(raw)
                        log.debug("Read Setting: Name=%s Value=%s Type=%s" % (s.localName, data, type(data)))
                        settings[s.localName] = data

            try:
                self.set_configuration(settings)
            except Exception, err: 
                log.warn("Error restoring %s configuration\n%s" % 
                        (self._name_, traceback.format_exc()))
        else:
            log.debug("Could not find <configuration> xml fragment")

    def get_UID(self):
        """
        Returns a UID that represents this dataproviders (locally) unique state
        and configuration. For example the LUID for a gmail dp may be your 
        username and password.

        Derived types MUST overwride this function
        @rtype: C{string}
        """
        raise NotImplementedError

    def get_input_conversion_args(self):
        """
        Provides a way to pass arguments to conversion functions. For example when 
        transcoding a music file the dataprovider may return a dictionary specifying the
        conversion encoding, quality, etc
        @returns: a C{dict} of conversion arguments
        """
        return {}

    def get_input_type(self):
        """
        Provides a way for dataproviders to change the datatype they accept. In most cases
        implementing get_in_conversion args is recommended and will let you acomplish what you want.
        @returs: A C{string} in the form "type_name?arg_name=foo&arg_name2=bar"
        """
        args = self.get_input_conversion_args()
        if len(args) == 0:
            return self._in_type_
        else:
            return "%s?%s" % (self._in_type_, Utils.encode_conversion_args(args))

    def get_output_conversion_args(self):
        """
        Provides a way to pass arguments to conversion functions. For example when 
        transcoding a music file the dataprovider may return a dictionary specifying the
        conversion encoding, quality, etc
        @returns: a C{dict} of conversion arguments
        """
        return {}

    def get_output_type(self):
        """
        Provides a way for dataproviders to change the datatype they emit. In most cases
        implementing get_out_conversion args is recommended and will let you acomplish what you want.
        @returs: A C{string} in the form "type_name?arg_name=foo&arg_name2=bar"
        """
        args = self.get_output_conversion_args()
        if len(args) == 0:
            return self._out_type_
        else:
            return "%s?%s" % (self._out_type_, Utils.encode_conversion_args(args))
            
    def get_name(self):
        """
        @returns: The DataProvider name, to be displayed in the UI
        """
        return self._name_
        
class DataSource(DataProviderBase):
    """
    Base Class for DataSources.
    """
    def __init__(self):
        DataProviderBase.__init__(self)
        
    def get(self, LUID):
        """
        Returns data with the specified LUID. This function must be overridden by the 
        appropriate dataprovider.

        Derived classes should call this function to ensure the dataprovider
        status is updated.

        @param LUID: The index of the data to return
        @type LUID: C{string}
        @rtype: L{conduit.DataType.DataType}
        @returns: An item of data
        """
        self.set_status(STATUS_SYNC)
        return None

    def get_num_items(self):
        """
        Returns the number of items requiring sychronization.
        @returns: The number of items to synchronize
        @rtype: C{int}
        """
        self.set_status(STATUS_SYNC)
        return len(self.get_all())
                
    def get_all(self):
        """
        Returns an array of all the LUIDs this dataprovider holds. 
        """
        self.set_status(STATUS_SYNC)
        return []

    def get_changes(self):
        """
        Returns all changes since last sync
        """
        raise NotImplementedError

    def add(self, LUID):
        """
        Adds an item to the datasource according to LUID. This method 
        is used by the DBus interface

        @returns: True if the data was successfully added
        """
        return False


class DataSink(DataProviderBase):
    """
    Base Class for DataSinks
    """
    def __init__(self):
        DataProviderBase.__init__(self)

    def put(self, putData, overwrite, LUID):
        """
        Stores data. The derived class is responsible for checking if putData
        conflicts. 
        
        In the case of a two-way datasource, the derived type should
        consider the overwrite parameter, which if True, should allow the dp
        to replace a datatype instance if one is found at the existing location

        Derived classes should call this function to ensure the dataprovider
        status is updated.

        @param putData: Data which to save
        @type putData: A L{conduit.DataType.DataType} derived type that this 
        dataprovider is capable of handling
        @param overwrite: If this argument is True, the DP should overwrite
        an existing datatype instace (if one exists). Generally used in conflict
        resolution. 
        @type overwrite: C{bool}
        @param LUID: A locally unique identifier representing the location
        where the data was previously put.
        @raise conduit.Exceptions.SynchronizeConflictError: if there is a 
        conflict between the data being put, and that which it is overwriting 
        a L{conduit.Exceptions.SynchronizeConflictError} is raised.
        """
        self.set_status(STATUS_SYNC)

    def delete(self, LUID):
        """
        Deletes data with LUID.
        """
        self.set_status(STATUS_SYNC)


class TwoWay(DataSource, DataSink):
    """
    Abstract Base Class for TwoWay dataproviders
    """
    def __init__(self):
        DataSource.__init__(self)
        DataSink.__init__(self)


class DataProviderFactory(gobject.GObject):
    """
    Abstract base class for a factory which emits Dataproviders. Users should 
    inherit from this if they wish to provide a loadable module in which
    dynamic dataproviders become available at runtime.
    """
    __gsignals__ = {
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT,      #Wrapper
            gobject.TYPE_PYOBJECT]),    #Class
        "dataprovider-removed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING])       #Unique key
    }

    _module_type_ = "dataprovider-factory"

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

    def emit_added(self, klass, initargs, category, customKey=None):
        dpw = ModuleWrapper.ModuleWrapper(   
                    klass=klass,
                    initargs=initargs,
                    category=category
                    )
        dpw.set_dnd_key(customKey)
        log.debug("DataProviderFactory %s: Emitting dataprovider-added for %s" % (self, dpw.get_dnd_key()))
        self.emit("dataprovider-added", dpw, klass)
        return dpw.get_dnd_key()

    def emit_removed(self, key):
        log.debug("DataProviderFactory %s: Emitting dataprovider-removed for %s" % (self, key))
        self.emit("dataprovider-removed", key)

    def probe(self):
        pass

    def quit(self):
        """
        Shutdown cleanup...
        """
        pass

    def get_configuration_widget(self):
        """
        If the factory needs to offer configuration options then
        it should return a gtk.widget here.
        """
        return None

    def save_configuration(self):
        """
        If the user closes the configuration panel with RESPONSE_OK (e.g.
        doesnt click cancel) then this will be called on all derived classes
        """
        pass
        

