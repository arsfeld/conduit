"""
Cotains classes for representing DataSources or DataSinks.

Copyright: John Stowers, 2006
License: GPLv2
"""

import gtk
import gtk.glade
import gobject
import goocanvas
from gettext import gettext as _

import logging
import conduit

#Constants used in the sync state machine
STATUS_NONE = 1
STATUS_REFRESH = 2
STATUS_DONE_REFRESH_OK = 3
STATUS_DONE_REFRESH_ERROR = 4
STATUS_SYNC = 5
STATUS_DONE_SYNC_OK = 6
STATUS_DONE_SYNC_ERROR = 7
STATUS_DONE_SYNC_SKIPPED = 8
STATUS_DONE_SYNC_CANCELLED = 9
STATUS_DONE_SYNC_CONFLICT = 10

#Tango colors taken from 
#http://tango.freedesktop.org/Tango_Icon_Theme_Guidelines
TANGO_COLOR_BUTTER_LIGHT = int("fce94fff",16)
TANGO_COLOR_BUTTER_MID = int("edd400ff",16)
TANGO_COLOR_BUTTER_DARK = int("c4a000ff",16)
TANGO_COLOR_ORANGE_LIGHT = int("fcaf3eff",16)
TANGO_COLOR_ORANGE_MID = int("f57900",16)
TANGO_COLOR_ORANGE_DARK = int("ce5c00ff",16)
TANGO_COLOR_CHOCOLATE_LIGHT = int("e9b96eff",16)
TANGO_COLOR_CHOCOLATE_MID = int("c17d11ff",16)
TANGO_COLOR_CHOCOLATE_DARK = int("8f5902ff",16)
TANGO_COLOR_CHAMELEON_LIGHT = int("8ae234ff",16)
TANGO_COLOR_CHAMELEON_MID = int("73d216ff",16)
TANGO_COLOR_CHAMELEON_DARK = int("4e9a06ff",16)
TANGO_COLOR_SKYBLUE_LIGHT = int("729fcfff",16)
TANGO_COLOR_SKYBLUE_MID = int("3465a4ff",16)
TANGO_COLOR_SKYBLUE_DARK = int("204a87ff",16)
TANGO_COLOR_PLUM_LIGHT = int("ad7fa8ff",16)
TANGO_COLOR_PLUM_MID = int("75507bff",16)
TANGO_COLOR_PLUM_DARK = int("5c3566ff",16)
TANGO_COLOR_SCARLETRED_LIGHT = int("ef2929ff",16)
TANGO_COLOR_SCARLETRED_MID = int("cc0000ff",16)
TANGO_COLOR_SCARLETRED_DARK = int("a40000ff",16)
TANGO_COLOR_ALUMINIUM1_LIGHT = int("eeeeecff",16)
TANGO_COLOR_ALUMINIUM1_MID = int("d3d7cfff",16)
TANGO_COLOR_ALUMINIUM1_DARK = int("babdb6ff",16)
TANGO_COLOR_ALUMINIUM2_LIGHT = int("888a85ff",16)
TANGO_COLOR_ALUMINIUM2_MID = int("555753ff",16)
TANGO_COLOR_ALUMINIUM2_DARK = int("2e3436ff",16)

#Constants affecting how the dataproviders are drawn onto the Canvas 
LINE_WIDTH = 3
RECTANGLE_RADIUS = 5
WIDGET_WIDTH = 120
WIDGET_HEIGHT = 80

class DataProviderCategory:
    def __init__(self, name, icon="image-missing", key=""):
        self.name = _(name)
        self.icon = icon
        self.key = name + key

CATEGORY_LOCAL = DataProviderCategory("On This Computer", "computer")
CATEGORY_REMOTE = DataProviderCategory("Remote", "network-server")
CATEGORY_WEB = DataProviderCategory("On The Web", "applications-internet")
CATEGORY_TEST = DataProviderCategory("Test")

class DataProviderBase(goocanvas.Group, gobject.GObject):
    """
    Model of a DataProvider. Can be a source or a sink
    
    @ivar name: The name of the module
    @type name: C{string}
    @ivar description: The name of the module
    @type description: C{string}
    @ivar widget: The name of the module
    @type widget: C{goocanvas.Group}
    @ivar widget_color: The background color of the base widget
    @type widget_color: C{string}    
    """
    
    __gsignals__ =  { 
                    "status-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }
    
    def __init__(self, widgetColorRGBA=0):
        """
        Handles a lot of the canvas and UI related aspects of a dataprovider
        All sync functionality should be provided by derived classes
        @param name: The name of the dataprovider to display on canvas
        @param widgetColorRGBA: RGBA integer color of the box in which the name
        description, and icon are drawn
        @type widgerColorRGBA: C{int}
        """
        goocanvas.Group.__init__(self)
        gobject.GObject.__init__(self)
        
        self.widgetColorRGBA = widgetColorRGBA

        self.icon = None
        self.status = STATUS_NONE
        #The following can be overridden to customize the appearance
        #of the basic dataproviders
        self.widget_width = WIDGET_WIDTH
        self.widget_height = WIDGET_HEIGHT
        
        #Build the child widgets
        self._build_widget()

    def __emit_status_changed(self):
        """
        Emits a 'status-changed' signal to the main loop.
        
        You should connect to this signal if you wish to be notified when
        the derived DataProvider goes through its stages (STATUS_* etc)
        """
        self.emit ("status-changed")
        return False        
        
    def _build_widget(self):
        """
        Drawing this widget by drawing all the items which represent a
        dataprovider, including the icon, text, etc
        """
        box = goocanvas.Rect(   x=0, 
                                y=0, 
                                width=self.widget_width, 
                                height=self.widget_height,
                                line_width=LINE_WIDTH, 
                                stroke_color="black",
                                fill_color_rgba=self.widgetColorRGBA, 
                                radius_y=RECTANGLE_RADIUS, 
                                radius_x=RECTANGLE_RADIUS
                                )
        name = goocanvas.Text(  x=int(2*self.widget_width/5), 
                                y=int(1*self.widget_height/3), 
                                width=3*self.widget_width/5, 
                                text=self._name_, 
                                anchor=gtk.ANCHOR_WEST, 
                                font="Sans 8"
                                )
        try:
            pb=gtk.icon_theme_get_default().load_icon(self._icon_, 16, 0)
            image = goocanvas.Image(pixbuf=pb,
                                    x=int(  
                                            (1*self.widget_width/5) - 
                                            (pb.get_width()/2) 
                                            ),
                                    y=int(  
                                            (1*self.widget_height/3) - 
                                            (pb.get_height()/2)
                                            )
                                                
                                    )
        except Exception, err:
            pass
        desc = goocanvas.Text(  x=int(1*self.widget_width/10), 
                                y=int(2*self.widget_height/3), 
                                width=4*self.widget_width/5, 
                                text=self._description_, 
                                anchor=gtk.ANCHOR_WEST, 
                                font="Sans 7",
                                fill_color_rgba=TANGO_COLOR_ALUMINIUM2_MID,
                                )                                    
    
       
        #Add all the visual elements which represent a dataprovider    
        self.add_child(box)
        self.add_child(name)
        #FIXME: This block of code does not work if in the above try-except
        #block. why? Who knows!
        try:
            self.add_child(image)
        except Exception, err:
            pass
        self.add_child(desc) 
            
    def get_widget_dimensions(self):
        """
        Returns the width of the DataProvider canvas widget.
        Should be overridden by those dataproviders which draw their own
        custom widgets
        
        @rtype: C{int}, C{int}
        @returns: width, height
        """
        return self.widget_width, self.widget_height
        
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
        dataprovider prior to calling get(). If possible it should gather 
        enough information so that get_num_items() can return a
        meaningful response
        
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
        pass

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
            
    def configure(self, window):
        """
        Show a configuration box for configuring the dataprovider instance.
        This call may block
        
        @param window: The parent window (to show a modal dialog)
        @type window: {gtk.Window}
        """
        logging.info("configure() not overridden by derived class %s" % self._name_)
        
    def get_configuration(self):
        """
        Returns a dictionary of strings to be saved, representing the dataproviders
        current configuration. Should be overridden by all dataproviders wishing
        to be able to save their state between application runs
        @returns: Dictionary of strings containing application settings
        @rtype: C{dict(string)}
        """
        logging.info("get_configuration() not overridden by derived class %s" % self._name_)
        return {}

    def set_configuration(self, config):
        """
        Restores applications settings
        @param config: dictionary of dataprovider settings to restore
        """
        logging.info("set_configuration() not overridden by derived class %s" % self._name_)
        for c in config:
            #Perform these checks to stop malformed xml from stomping on
            #unintended variables or posing a security risk by overwriting methods
            if getattr(self, c, None) != None and callable(getattr(self, c, None)) == False:
                logging.debug("Setting %s to %s" % (c, config[c]))
                setattr(self,c,config[c])
            else:
                logging.warn("Not restoring %s setting: Exists=%s Callable=%s" % (
                    c,
                    getattr(self, c, False),
                    callable(getattr(self, c, None)))
                    )

class DataSource(DataProviderBase):
    """
    Base Class for DataSources.
    """
    def __init__(self, widgetColorRGBA=TANGO_COLOR_ALUMINIUM1_MID):
        """
        Sets the DataProvider color
        """
        DataProviderBase.__init__(self, widgetColorRGBA)
        
    def get(self, index):
        """
        Returns data at specified index. This function must be overridden by the 
        appropriate dataprovider.

        Derived classes should call this function to ensure the dataprovider
        status is updated.

        It is expected that you may call this function with numbers in the 
        range 0 -> L{conduit.DataProvider.DataSource.get_num_items}.
        
        @param index: The index of the data to return
        @type index: C{int}
        @rtype: L{conduit.DataType.DataType}
        @returns: An item of data
        """
        self.set_status(STATUS_SYNC)
        return None
                
    def get_num_items(self):
        """
        Returns the number of items requiring sychronization. This function 
        must be overridden by the appropriate dataprovider.
        
        @returns: The number of items to synchronize
        @rtype: C{int}
        """
        self.set_status(STATUS_SYNC)
        return 0

class DataSink(DataProviderBase):
    """
    Base Class for DataSinks
    """
    def __init__(self, widgetColorRGBA=TANGO_COLOR_SKYBLUE_LIGHT):
        """
        Sets the DataProvider color
        """    
        DataProviderBase.__init__(self, widgetColorRGBA)

    def put(self, putData, overwrite):
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
        dataprovider is capable of handling        
        @raise conduit.Exceptions.SynchronizeConflictError: if there is a 
        conflict between the data being put, and that which it is overwriting 
        a L{conduit.Exceptions.SynchronizeConflictError} is raised.
        """
        self.set_status(STATUS_SYNC)

class TwoWay(DataSource, DataSink):
    """
    Abstract Base Class for TwoWay dataproviders
    """
    def __init__(self, widgetColorRGBA=TANGO_COLOR_BUTTER_MID):
        """
        Sets the DataProvider color
        """
        DataSource.__init__(self, widgetColorRGBA)
        DataSink.__init__(self, widgetColorRGBA)


        

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
        logging.debug("OK Clicked")
        for w in self.widgetInstances:
            #FIXME: This seems hackish
            if isinstance(w["Widget"], gtk.Entry):
                w["Callback"](w["Widget"].get_text())
            elif isinstance(w["Widget"], gtk.CheckButton):
                w["Callback"](w["Widget"].get_active())
            else:
                logging.warn("Dont know how to retrieve value from a %s" % w["Widget"])

        self.dialog.destroy()
        
    def on_cancel_clicked(self, widget):
        """
        on_cancel_clicked
        """
        logging.debug("Cancel Clicked")
        self.dialog.destroy()
        
    def on_help_clicked(self, widget):
        """
        on_help_clicked
        """
        logging.debug("Help Clicked")
        
    def on_dialog_close(self, widget):
        """
        on_dialog_close
        """
        logging.debug("Dialog Closed")
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
        
