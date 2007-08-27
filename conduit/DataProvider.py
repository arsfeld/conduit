"""
Cotains classes for representing DataSources or DataSinks.

Copyright: John Stowers, 2006
License: GPLv2
"""

import gtk, gtk.glade
import gobject
from gettext import gettext as _
import xml.dom.minidom
import traceback

import conduit
from conduit import log,logd,logw
import conduit.ModuleWrapper as ModuleWrapper
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

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

class DataProviderCategory:
    def __init__(self, name, icon="image-missing", key=""):
        self.name = _(name)
        self.icon = icon
        self.key = name + key

#Default Categories for the DataProviders
CATEGORY_FILES = DataProviderCategory("Files and Folders", "computer")
CATEGORY_NOTES = DataProviderCategory("Notes", "tomboy")
CATEGORY_PHOTOS = DataProviderCategory("Photos", "image-x-generic")
CATEGORY_OFFICE = DataProviderCategory("Office", "applications-office")
CATEGORY_SETTINGS = DataProviderCategory("Settings", "applications-system")
CATEGORY_MISC = DataProviderCategory("Miscellanous", "applications-accessories")
CATEGORY_MEDIA = DataProviderCategory("Media", "applications-media")
CATEGORY_TEST = DataProviderCategory("Test")

class DataProviderBase(gobject.GObject):
    """
    Model of a DataProvider. Can be a source or a sink
    """
    
    __gsignals__ =  { 
                    "status-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "change-detected": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }
    
    def __init__(self):
        """
        All sync functionality should be provided by derived classes
        """
        gobject.GObject.__init__(self)

        self.pendingChangeDetected = False
        self.icon = None
        self.status = STATUS_NONE

        #track the state of widget configuration
        self.need_configuration(False)
        self.set_configured(False)

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
        logd("Change detected in dataproviders data (%s)" % self.get_UID())

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
        
    def refresh(self):
        """
        Performs any (logging in, etc) which must be undertaken on the 
        dataprovider prior to calling get_all(). Should gather all information
        so a subsequent call to get_all() can return the uids of all the
        data this dataprovider holds
        
        This function may be called multiple times so derived classes should
        be aware of this.

        Derived classes should call this function to ensure the dataprovider
        status is updated.
        """
        self.set_status(STATUS_REFRESH)

    def finish(self):
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
        if newStatus != self.status:
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
        s = self.status
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
        s = self.status
        if s == STATUS_REFRESH:
            return True
        elif s == STATUS_SYNC:
            return True
        else:
            return False

    def need_configuration(self, need):
        """
        Derived classes should call this function in their constructor if they
        require configuration before they can operate
        """
        self.needConfiguration = need

    def set_configured(self, configured):
        """
        Sets if the widget has been configured or not. Derived classes may call 
        this for example, to ensure the user enters the configure menu
        """
        self.isConfigured = configured
            
    def configure(self, window):
        """
        Show a configuration box for configuring the dataprovider instance.
        This call may block
        
        @param window: The parent window (to show a modal dialog)
        @type window: {gtk.Window}
        """
        logd("configure() not overridden by derived class %s" % self._name_)
        self.set_configured(True)

    def is_configured(self):
        """
        Checks if the dp has been configured or not (and if it needs to be)
        """
        return (not self.needConfiguration) or self.isConfigured
        
    def get_configuration(self):
        """
        Returns a dictionary of strings to be saved, representing the dataproviders
        current configuration. Should be overridden by all dataproviders wishing
        to be able to save their state between application runs
        @returns: Dictionary of strings containing application settings
        @rtype: C{dict(string)}
        """
        logd("get_configuration() not overridden by derived class %s" % self._name_)
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
                    vtype = conduit.Settings.Settings.TYPE_TO_TYPE_NAME[ type(configDict[config]) ]
                    value = conduit.Settings.Settings.TYPE_TO_STRING[  type(configDict[config]) ](configDict[config])
                except KeyError:
                    logw("Cannot convert %s to string. Value of %s not saved" % (type(value), config))
                    vtype = conduit.Settings.Settings.TYPE_TO_TYPE_NAME[str]
                    value = conduit.Settings.Settings.TYPE_TO_STRING[str](configDict[config])
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
        logd("set_configuration() not overridden by derived class %s" % self._name_)
        for c in config:
            #Perform these checks to stop malformed xml from stomping on
            #unintended variables or posing a security risk by overwriting methods
            if getattr(self, c, None) != None and callable(getattr(self, c, None)) == False:
                logd("Setting %s to %s" % (c, config[c]))
                setattr(self,c,config[c])
            else:
                logw("Not restoring %s setting: Exists=%s Callable=%s" % (
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
                            data = conduit.Settings.Settings.STRING_TO_TYPE[vtype](raw)
                        except KeyError:
                            #fallback to string type
                            logw("Cannot convert string (%s) to native type %s\n" % (raw, vtype, traceback.format_exc()))
                            data = str(raw)
                        logd("Read Setting: Name=%s Value=%s Type=%s" % (s.localName, data, type(data)))
                        settings[s.localName] = data

            try:
                self.set_configuration(settings)
            except Exception, err: 
                logw("Error restoring %s configuration\n%s" % 
                        (self._name_, traceback.format_exc()))
        else:
            logd("Could not find <configuration> xml fragment")

    def get_UID(self):
        """
        Returns a UID that represents this dataproviders (locally) unique state
        and configuration. For example the LUID for a gmail dp may be your 
        username and password.

        Derived types MUST overwride this function
        @rtype: C{string}
        """
        raise NotImplementedError

    def get_in_type(self):
        """
        Provides a way for dataproviders to configure what format they want 
        at runtime.
        """
        return self._in_type_

    def get_out_type(self):
        """
        Provides a way for dataproviders to configure what format they want 
        at runtime.
        """
        return self._out_type_


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

class ImageSink(DataSink):
    """
    Abstract Base class for Image DataSinks
    """
    _category_ = CATEGORY_PHOTOS
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"

    ALLOWED_MIMETYPES = ["image/jpeg", "image/png"]
    
    def __init__(self, *args):
        DataSink.__init__(self)
        self.need_configuration(True)
        
        self.username = ""

    def initialize(self):
        return True

    def _get_photo_info(self, photoID):
        """
        This should return the info for a given photo id,
        If this returns anything different from None, it will be
        passed onto _get_raw_photo_url 
        """
        return None

    def _get_raw_photo_url(self, photoInfo):
        """
        This should return the url of the online photo
        """
        return None

    def _upload_photo (self, url, mimeType, name):
        """
        Upload a photo
        """
        return None 

    def _replace_photo (self, id, url, mimeType, name):
        """
        Replace a photo with a new version
        """
        return id

    def put(self, photo, overwrite, LUID=None):
        """
        Accepts a vfs file. Must be made local.
        I also store a md5 of the photos uri to check for duplicates
        """
        DataSink.put(self, photo, overwrite, LUID)

        originalName = photo.get_filename()
        #Gets the local URI (/foo/bar). If this is a remote file then
        #it is first transferred to the local filesystem
        photoURI = photo.get_local_uri()

        mimeType = photo.get_mimetype()
        if mimeType not in self.ALLOWED_MIMETYPES:
            raise Exceptions.SyncronizeError("%s does not allow uploading %s Files" % (self._name_, mimeType))
        
        #Check if we have already uploaded the photo
        if LUID != None:
            info = self._get_photo_info(LUID)
            #check if a photo exists at that UID
            if info != None:
                if overwrite == True:
                    #replace the photo
                    return self._replace_photo(LUID, photoURI, mimeType, originalName)
                else:
                    #Only upload the photo if it is newer than the Remote one
                    url = self._get_raw_photo_url(info)
                    remoteFile = File.File(url)

                    #this is a limited test for equality type comparison
                    comp = photo.compare(remoteFile,True)
                    logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (photo.get_filename(),remoteFile.get_filename(),comp))
                    if comp != conduit.datatypes.COMPARISON_EQUAL:
                        raise Exceptions.SynchronizeConflictError(comp, photo, remoteFile)
                    else:
                        return LUID

        logd("Uploading Photo URI = %s, Mimetype = %s, Original Name = %s" % (photoURI, mimeType, originalName))

        #upload the file
        return self._upload_photo (photoURI, mimeType, originalName)

    def delete(self, LUID):
        pass
 
    def is_configured (self):
        return False
        
    def set_configuration(self, config):
        DataSink.set_configuration(self, config)
        self.set_configured(self.is_configured())
    

class DataProviderSimpleConfigurator:
    """
    Provides a simple modal configuration dialog for dataproviders.
    
    Simply provide a list of dictionarys in the following format::
    
        maps = [
                    {
                    "Name" : "Setting Name",
                    "Widget" : gtk.TextView,
                    "Callback" : function,
                    "InitialValue" : value
                    }
                ]
    """
    
    CONFIG_WINDOW_TITLE_TEXT = _("Configure ")
    
    def __init__(self, window, dp_name, config_mappings = []):
        """
        @param window: Parent window (this dialog is modal)
        @type window: C{gtk.Window}
        @param dp_name: The dataprovider name to display in the dialog title
        @type dp_name: C{string}
        @param config_mappings: The list of dicts explained earlier
        @type config_mappings: C{[{}]}
        """
        self.mappings = config_mappings
        #need to store ref to widget instances
        self.widgetInstances = []
        self.dialogParent = window
        #the child widget to contain the custom settings
        self.customSettings = gtk.VBox(False, 5)
        
        #The dialog is loaded from a glade file
        widgets = gtk.glade.XML(conduit.GLADE_FILE, "DataProviderConfigDialog")
        callbacks = {
                    "on_okbutton_clicked" : self.on_ok_clicked,
                    "on_cancelbutton_clicked" : self.on_cancel_clicked,
                    "on_helpbutton_clicked" : self.on_help_clicked,
                    "on_dialog_close" : self.on_dialog_close
                    }
        widgets.signal_autoconnect(callbacks)
        self.dialog = widgets.get_widget("DataProviderConfigDialog")
        self.dialog.set_transient_for(self.dialogParent)
        self.dialog.set_title(DataProviderSimpleConfigurator.CONFIG_WINDOW_TITLE_TEXT + dp_name)

        #The contents of the dialog are built from the config mappings list
        self.build_child()
        vbox = widgets.get_widget("configVBox")
        vbox.pack_start(self.customSettings)
        self.customSettings.show_all()        
        
    def on_ok_clicked(self, widget):
        """
        on_ok_clicked
        """
        logd("OK Clicked")
        for w in self.widgetInstances:
            #FIXME: This seems hackish
            if isinstance(w["Widget"], gtk.Entry):
                w["Callback"](w["Widget"].get_text())
            elif isinstance(w["Widget"], gtk.CheckButton):
                w["Callback"](w["Widget"].get_active())
            else:
                logw("Dont know how to retrieve value from a %s" % w["Widget"])

        self.dialog.destroy()
        
    def on_cancel_clicked(self, widget):
        """
        on_cancel_clicked
        """
        logd("Cancel Clicked")
        self.dialog.destroy()
        
    def on_help_clicked(self, widget):
        """
        on_help_clicked
        """
        logd("Help Clicked")
        
    def on_dialog_close(self, widget):
        """
        on_dialog_close
        """
        logd("Dialog Closed")
        self.dialog.destroy()                       

    def run(self):
        """
        run
        """
        resp = self.dialog.run()
        
    def build_child(self):
        """
        For each item in the mappings list create the appropriate widget
        """
        #For each item in the mappings list create the appropriate widget
        for l in self.mappings:
            #New instance of the widget
            widget = l["Widget"]()
            #all get packed into an HBox
            hbox = gtk.HBox(False, 5)

            #FIXME: I am ashamed about this ugly hackery and dupe code....
            if isinstance(widget, gtk.Entry):
                #gtkEntry has its label beside it
                label = gtk.Label(l["Name"])
                hbox.pack_start(label)
                widget.set_text(str(l["InitialValue"]))
            elif isinstance(widget, gtk.CheckButton):
                #gtk.CheckButton has its label built in
                widget = l["Widget"](l["Name"])
                widget.set_active(bool(l["InitialValue"]))                        
                #FIXME: There must be a better way to do this but we need some way 
                #to identify the widget *instance* when we save the values from it
            self.widgetInstances.append({
                                        "Widget" : widget,
                                        "Callback" : l["Callback"]
                                        })
            #pack them all together
            hbox.pack_start(widget)
            self.customSettings.pack_start(hbox)

class DataProviderFactory(gobject.GObject):
    """
    Abstract base class for a factory which emits Dataproviders. Users should 
    inherit from this if they wish to provide a loadable module in which
    dynamic dataproviders become available at runtime.
    """
    __gsignals__ = {
        "dataprovider-available" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT,      #Wrapper
            gobject.TYPE_PYOBJECT]),    #Class
        "dataprovider-unavailable" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING])     #Unique key
    }

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

    def emit_added(self, klass, initargs=(), category=None):
        if category == None:
            category = getattr(klass, "_category_", CATEGORY_TEST)
        dpw = ModuleWrapper.ModuleWrapper (   
                    getattr(klass, "_name_", ""),
                    getattr(klass, "_description_", ""),
                    getattr(klass, "_icon_", ""),
                    getattr(klass, "_module_type_", ""),
                    category,
                    getattr(klass, "_in_type_", ""),
                    getattr(klass, "_out_type_", ""),
                    klass.__name__,     #classname
                    initargs,
                    )
        logd("DataProviderFactory %s: Emitting dataprovider-available for %s" % (self, dpw.get_key()))
        self.emit("dataprovider-available", dpw, klass)
        return dpw.get_key()

    def emit_removed(self, key):
        logd("DataProviderFactory %s: Emitting dataprovider-unavailable for %s" % (self, key))
        self.emit("dataprovider-unavailable", key)

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
        
