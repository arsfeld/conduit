import gtk
import gtk.glade
import gobject
import goocanvas
from gettext import gettext as _

import logging
import conduit

STATUS_NONE = 1
STATUS_INIT = 2
STATUS_DONE_INIT_OK = 3
STATUS_DONE_INIT_ERROR = 4
STATUS_SYNC = 5
STATUS_DONE_SYNC_OK = 6
STATUS_DONE_SYNC_ERROR = 7

class DataProviderBase(gobject.GObject):
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
    
    __gsignals__ = { 'status-changed': (gobject.SIGNAL_RUN_FIRST, 
                                        gobject.TYPE_NONE,      #return type
                                        (gobject.TYPE_INT,)     #argument
                                        )}
    
    def __init__(self, name=None, description=None):
        """
        Test
        """
        gobject.GObject.__init__(self)
        
        self.name = name
        self.description = description
        self.icon = None
        self.widget = None
        self.status = STATUS_NONE
        #The following can be overridden to customize the appearance
        #of the basic dataproviders
        self.icon_name = gtk.STOCK_OK        
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM2_LIGHT
        self.widget_width = 120
        self.widget_height = 80
        
    def __emit_status_changed(self):
		"""
		Emits a 'status-changed' signal to the main loop.
		
		You should connect to this signal if you wish to be notified when
		the derived DataProvider goes through its stages (STATUS_* etc)
		"""
		self.emit ("status-changed",self.status)
		return False        
        
    def get_icon(self):
        """
        Returns a GdkPixbuf hat represents this handler.
        """
        if self.icon is None:
            try:
                self.icon = gtk.icon_theme_get_default().load_icon(self.icon_name, 16, 0)
            except:
                self.icon = None
                logging.error("Could not load icon %s" % self.icon_name)
        return self.icon
        
    def get_widget(self):
        """
        Returns the goocanvas item for drawing this widget on the canvas. 
        Subclasses may override this method to draw more custom widgets
        """
        #Create it the first time
        if self.widget is None:
            self.widget = goocanvas.Group()
            box = goocanvas.Rect(   x=0, 
                                    y=0, 
                                    width=self.widget_width, 
                                    height=self.widget_height,
                                    line_width=3, 
                                    stroke_color="black",
                                    fill_color_rgba=self.widget_color_rgba, 
                                    radius_y=5, 
                                    radius_x=5
                                    )
            name = goocanvas.Text(  x=int(2*self.widget_width/5), 
                                    y=int(1*self.widget_height/3), 
                                    width=3*self.widget_width/5, 
                                    text=self.name, 
                                    anchor=gtk.ANCHOR_WEST, 
                                    font="Sans 8"
                                    )
            pb=self.get_icon()
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
            desc = goocanvas.Text(  x=int(1*self.widget_width/10), 
                                    y=int(2*self.widget_height/3), 
                                    width=4*self.widget_width/5, 
                                    text=self.description, 
                                    anchor=gtk.ANCHOR_WEST, 
                                    font="Sans 7",
                                    fill_color_rgba=TANGO_COLOR_ALUMINIUM2_MID,
                                    )                                    
        
            #We need some way to tell the canvas that we are a dataprovider
            #and not a conduit
            self.widget.set_data("is_a_dataprovider",True)
            
            self.widget.add_child(box)
            self.widget.add_child(name)
            self.widget.add_child(image)
            self.widget.add_child(desc) 
            
        return self.widget
        
    def get_widget_dimensions(self):
        """
        Returns the width of the DataProvider canvas widget.
        Should be overridden by those dataproviders which draw their own
        custom widgets
        
        @rtype: C{int}, C{int}
        @returns: width, height
        """
        return self.widget_width, self.widget_height
        
    def deserialize(self, class_name, serialized):
        """
        Deserialize
        """
        logging.warn("deserialize() not overridden by derived class %s" % self.name)
        #try:
        #	match = getattr(sys.modules[self.__module__], class_name)(self, **serialized)
        #	if match.is_valid():
        #		return match
        #except Exception, msg:
        #	print 'Warning:Error while deserializing match:', class_name, serialized, msg
        #return None

    def serialize(self, class_name):
        """
        Serializes (pickles) the dataprovider for sending over network.
        Designed to be used with avahi sync
        @todo: Should this be a funtion in modulewrapper??
        """
        logging.warn("serialize() not overridden by derived class %s" % self.name)
        
    def initialize(self):
        """
        Performs any initialization steps (logging in, etc) which must
        be undertaken on the dataprovider. 
        
        Derived types should override this function but still call it.
        
        This will only be called once (or 
        if the dataprovider had been finalized).
        """
        self.set_status(STATUS_INIT)
        
    def finalize(self):
        """
        Called after all tasks related to the dataprovider have been completed
        """
        logging.warn("finalize() not overridden by derived class %s" % self.name)
        
    def get_status(self):
        return self.status
        
    def get_status_text(self):
        s = self.status
        if s == STATUS_NONE:
            return _("Ready")
        elif s == STATUS_INIT:
            return _("Initializing...")
        elif s == STATUS_DONE_INIT_OK:
            return _("Initialized OK")
        elif s == STATUS_DONE_INIT_ERROR:
            return _("Initialization Error")
        elif s == STATUS_SYNC:
            return _("Synchronizing...")
        elif s == STATUS_DONE_SYNC_OK:
            return _("Synchronized OK")
        elif s == STATUS_DONE_SYNC_ERROR:
            return _("Synchronization Error")
        else:
            return "BAD PROGRAMMER"

    def set_status(self, newStatus):
        if newStatus != self.status:
            self.status = newStatus
            self.__emit_status_changed()

    def configure(self, window):
        """
        Show a configuration box for configuring the dataprovider instance.
        This call may block
        
        @param window: The parent window (to show a modal dialog)
        @type window: {gtk.Window}
        """
        logging.warn("configure() not overridden by derived class %s" % self.name)
        
    def put(self, data):
        """
        Stores data.

        Checks if the dataprovider has been initialized first, if not then
        calls .initialize(). This function must be overridden by the 
        appropriate dataprovider but derived classes must still call this 
        function.

        @param data_type: Data which to save
        @type data_type: A L{conduit.DataType.DataType} derived type that this 
        dataprovider is capable of handling
        @rtype: C{bool}
        @returns: True for success, false on failure
        """
        if self.status < STATUS_INIT:
            self.initialize()
        self.set_status(STATUS_SYNC)
                
    def get(self):
        """
        Returns all appropriate data. 
        
        Checks if the dataprovider has been initialized first, if not then
        calls .initialize(). This function must be overridden by the 
        appropriate dataprovider but derived classes must still call this 
        function.
        
        @rtype: L{conduit.DataType.DataType}[]
        @returns: An array of all data needed for synchronization and provided
        through configuration by this dataprovider.
        """
        if self.status < STATUS_INIT:
            self.initialize()
        self.set_status(STATUS_SYNC)
        
    def get_num_items(self):
        """
        Returns the number of items requiring sychronization. This function 
        must be overridden by the appropriate dataprovider.
        @todo: Use this to make a progress dialog and does this number 
        represent the number of times that get shall be called??
        
        @returns: The number of items to synchronize
        @rtype: C{int}
        """
        logging.warn("get_num_items() not overridden by derived class %s" % self.name)
        return NO_ITEMS

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

class DataSource(DataProviderBase):
    """
    Base Class for DataSources
    """
    def __init__(self, name=None, description=None):
        DataProviderBase.__init__(self, name, description)
        
        #customizations
        self.icon_name = "gtk-media-next"
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM1_MID
  
class DataSink(DataProviderBase):
    """
    Base Class for DataSinks
    """
    def __init__(self, name=None, description=None):
        #super fills in the name and description
        DataProviderBase.__init__(self, name, description)

        #customizations
        self.icon_name = "gtk-media-previous"
        self.widget_color_rgba = TANGO_COLOR_SKYBLUE_LIGHT
 
class DataProviderTreeModel(gtk.GenericTreeModel):
    """
    A treemodel for managing dynamically loaded modules. Manages an internal 
    list of L{conduit.ModuleManager.ModuleWrapper}
    
    @ivar modules: The array of modules under this treeviews control.
    @type modules: L{conduit.ModuleManager.ModuleWrapper}[]
    """
    column_types = (gtk.gdk.Pixbuf, str, str)
    column_names = ['Name', 'Description']

    def __init__(self, module_wrapper_list):
        gtk.GenericTreeModel.__init__(self)
        #print "init, array= ", module_array
        self.module_wrapper_list = module_wrapper_list
        return 
        
    def get_module_index_by_name(self, name):
        """
        get
        """
        #print "get_module_index_by_name: name = ", name
        for n in range(0, len(self.module_wrapper_list)):
            if self.module_wrapper_list[n].name == name:
                return n
                
    def get_module_by_name(self, name):
        """
        get mod
        """
        #TODO: ERROR CHECK
        return self.module_wrapper_list[self.get_module_index_by_name(name)]
    
    def get_column_names(self):
        """
        get_column_names(
        """
        return self.column_names[:]

    def on_get_flags(self):
        """
        on_get_flags(
        """
        return gtk.TREE_MODEL_LIST_ONLY|gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        """
        on_get_n_columns(
        """
        return len(self.column_types)

    def on_get_column_type(self, n):
        """
        on_get_column_type(
        """
        return self.column_types[n]

    def on_get_iter(self, path):
        #print "on_get_iter: path =", path
        """
        on_get_iter(
        """
        try:
            return self.module_wrapper_list[path[0]].name
        except IndexError:
            #no modules loaded
            return None

    def on_get_path(self, rowref):
        #print "on_get_path: rowref = ", rowref
        """
        on_get_path(
        """
        return self.module_wrapper_list[self.get_module_index_by_name(rowref)]

    def on_get_value(self, rowref, column):
        """
        on_get_value(
        """
        #print "on_get_value: rowref = %s column = %s" % (rowref, column)
        m = self.module_wrapper_list[self.get_module_index_by_name(rowref)]
        if column is 0:
            return m.module.get_icon()
        elif column is 1:
            return m.name
        elif column is 2:
            return m.description
        else:
            print "ERROR WILL ROBINSON"
            return None
        
    def on_iter_next(self, rowref):
        """
        on_iter_next(
        """
        #print "on_iter_next: rowref = ", rowref
        try:
            i = self.get_module_index_by_name(rowref)
            #print "on_iter_next: old i = ", i
            i = i+1
            #print "on_iter_next: next i = ", i
            return self.module_wrapper_list[i].name
        except IndexError:
            return None
        
    def on_iter_children(self, rowref):
        """
        on_iter_children(
        """
        #print "on_iter_children: rowref = ", rowref
        if rowref:
            return None
        return self.module_wrapper_list[0].name

    def on_iter_has_child(self, rowref):
        """
        on_iter_has_child(
        """
        #print "on_iter_has_child: rowref = ", rowref
        return False

    def on_iter_n_children(self, rowref):
        """
        on_iter_n_children(
        """
        #print "on_iter_n_children: rowref = ", rowref
        if rowref:
            return 0
        return len(self.module_wrapper_list)

    def on_iter_nth_child(self, rowref, n):
        """
        on_iter_nth_child(
        """
        #print "on_iter_nth_chile: rowref = %s n = %s" % (rowref, n)
        if rowref:
            return None
        try:
            return self.module_wrapper_list[n].name
        except IndexError:
            return None

    def on_iter_parent(child):
        """
        on_iter_parent(
        """
        #print "on_iter_parent: child = ", child
        return None
        
class DataProviderTreeView(gtk.TreeView):
    DND_TARGETS = [
    ('conduit/element-name', 0, 2)
    ]
    def __init__(self, model):
        gtk.TreeView.__init__(self, model)
        
        column_names = model.get_column_names()
        tvcolumn = [None] * len(column_names)
        # First column is an image and the name...
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()
        tvcolumn[0] = gtk.TreeViewColumn(column_names[0],cellpb, pixbuf=0)
        tvcolumn[0].pack_start(cell, False)
        tvcolumn[0].add_attribute(cell, 'text', 1)
        self.append_column(tvcolumn[0])
        # Second cell is description
        tvcolumn[1] = gtk.TreeViewColumn(column_names[1], gtk.CellRendererText(), text=2)
        self.append_column(tvcolumn[1])
        
        # DND info:
        # drag
        self.enable_model_drag_source(  gtk.gdk.BUTTON1_MASK,
                                        DataProviderTreeView.DND_TARGETS,
                                        gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
        self.drag_source_set(           gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                                        DataProviderTreeView.DND_TARGETS,
                                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-data-get', self.on_drag_data_get)
        self.connect('drag-data-delete', self.on_drag_data_delete)
    
    def on_drag_data_get(self, treeview, context, selection, target_id, etime):
        """
        Get the data to be dropped by on_drag_data_received().
        We send the id of the dragged element.
        """
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        data = model.get_value(iter, 1)
        #print "---------------------------- data = ", data
        selection.set(selection.target, 8, data)
        
    def on_drag_data_delete (self, context, etime):
        """
        DnD magic. do not touch
        """
        self.emit_stop_by_name('drag-data-delete')      
        #context.finish(True, True, etime)        
        
class DataProviderSimpleConfigurator:
    """
    Provides a simple modal configuration dialog for dataproviders.
    
    Simply provide a list of dictionarys in the following format::
    
        maps = [
                    {
                    "Name" : "Setting Name",
                    "Widget" : gtk.TextView,
                    "Callback" : function
                    }
                ]
    """
    
    CONFIG_WINDOW_TITLE_TEXT = _("Configure ")
    
    def __init__(self, window, dp_name, config_mappings = []):
        """
        @param window: Parent window (this dialog is modal)
        @type window: C{gtk.Window}
        @param dp_name: The dataprovider name to display in the dialog title
        @type title: C{string}
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
        logging.debug("Cancel Clicked")
        self.dialog.destroy()
        
    def on_help_clicked(self, widget):
        logging.debug("Help Clicked")
        
    def on_dialog_close(self, widget):
        logging.debug("Dialog Closed")
        self.dialog.destroy()                       

    def run(self):
        resp = self.dialog.run()
        
    def build_child(self):
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
            elif isinstance(widget, gtk.CheckButton):
                #gtk.CheckButton has its label built in
                widget = l["Widget"](l["Name"])
                        
                #FIXME: There must be a better way to do this but we need some way 
                #to identify the widget *instance* when we save the values from it
            self.widgetInstances.append({
                                        "Widget" : widget,
                                        "Callback" : l["Callback"]
                                        })
            #pack them all together
            hbox.pack_start(widget)
            self.customSettings.pack_start(hbox)
        
