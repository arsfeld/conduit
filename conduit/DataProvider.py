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

#List of availabel categories that dataproviders can belong. 
CATEGORY_LOCAL = "Local"
CATEGORY_WEB = "Web"
CATEGORY_GOOGLE = "Google"

#Store the translated catgory names
CATEGORY_NAMES = {
    CATEGORY_LOCAL : _("On This Computer"),
    CATEGORY_WEB : _("On The Web"),
    CATEGORY_GOOGLE : _("Google")
    }

#Icon names for each category
CATEGORY_ICONS = {
    CATEGORY_LOCAL : "computer",
    CATEGORY_WEB : "applications-internet",
    CATEGORY_GOOGLE : "applications-internet"
    } 

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
    
    __gsignals__ =  { 
                    "status-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }
    
    def __init__(self, name=None, description=None):
        """
        Makes a (useless) base dataprovider
        """
        gobject.GObject.__init__(self)
        
        self.name = name
        self.description = description
        self.icon = None
        self.widget = None
        self.status = STATUS_NONE
        #The following can be overridden to customize the appearance
        #of the basic dataproviders
        self.icon_name = "gtk-missing-image"   
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM2_LIGHT
        self.widget_width = WIDGET_WIDTH
        self.widget_height = WIDGET_HEIGHT
        
        #EXPERIMENTAL: Set this to True to enable two-way sync
        self.twoWayEnabled = False
        
    def __emit_status_changed(self):
		"""
		Emits a 'status-changed' signal to the main loop.
		
		You should connect to this signal if you wish to be notified when
		the derived DataProvider goes through its stages (STATUS_* etc)
		"""
		self.emit ("status-changed")
		return False        
        
    def get_icon(self):
        """
        Returns a GdkPixbuf hat represents this handler.
        """
        import traceback
        if self.icon is None:
            try:
                self.icon = gtk.icon_theme_get_default().load_icon(self.icon_name, 16, 0)
            except gobject.GError:
                self.icon = None
                logging.error("Could not load icon %s" % self.icon_name)
                self.icon = gtk.icon_theme_get_default().load_icon("gtk-missing-image", 16, 0)
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
                                    line_width=LINE_WIDTH, 
                                    stroke_color="black",
                                    fill_color_rgba=self.widget_color_rgba, 
                                    radius_y=RECTANGLE_RADIUS, 
                                    radius_x=RECTANGLE_RADIUS
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
        logging.info("initialize() not overridden by derived class %s" % self.name)
        return True
        
    def refresh(self):
        """
        Performs any (logging in, etc) which must be undertaken on the 
        dataprovider prior to calling get(). If possible it should gather 
        enough information so that get_num_items() can return a
        meaningful response
        
        THis function may be called multiple times so derived funcions should
        be aware of this
        """
        logging.info("refresh() not overridden by derived class %s" % self.name)
        
    def finalize(self):
        """
        Called after all tasks related to the dataprovider have been completed
        """
        logging.info("finalize() not overridden by derived class %s" % self.name)
        
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
            
    def is_two_way_enabled(self):
        """
        Determines if the DataProvider supports two-way synchronization. This
        is true if it implements get(), put() and explicitly 
        sets self.twoWayEnabled to True
        """
        return self.is_two_way() and self.twoWayEnabled
            
    def is_two_way(self):
        """
        If the derived dataprovider includes both get() and set() then
        it is considered to support two way sync. We still need to
        check that it is enabled, it might eat your children
        
        A Default DataProvider does not support two-way sync. 
        See L{conduit.DataProvider.DataSource.is_two_way}
        """
        return False

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

    def configure(self, window):
        """
        Show a configuration box for configuring the dataprovider instance.
        This call may block
        
        @param window: The parent window (to show a modal dialog)
        @type window: {gtk.Window}
        """
        logging.info("configure() not overridden by derived class %s" % self.name)
        
    def get_configuration(self):
        """
        Returns a dictionary of strings to be saved, representing the dataproviders
        current configuration. Should be overridden by all dataproviders wishing
        to be able to save their state between application runs
        @returns: Dictionary of strings containing application settings
        @rtype: C{dict(string)}
        """
        logging.info("get_configuration() not overridden by derived class %s" % self.name)
        return {}

    def set_configuration(self, config):
        """
        Restores applications settings
        @param config: dictionary of dataprovider settings to restore
        """
        logging.info("set_configuration() not overridden by derived class %s" % self.name)
        for c in config:
            #Perform these checks to stop malformed xml from stomping on
            #unintended variables or posing a security risk by overwriting methods
            if getattr(self, c, None) != None and callable(getattr(self, c, None)) == False:
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
    
    DataSources can become two way datasources if they also override
    put() and set twoWayEnable to True
    """
    def __init__(self, name=None, description=None):
        """
        Sets the DataProvider color and a default icon
        """
        DataProviderBase.__init__(self, name, description)
        
        #customizations
        self.icon_name = "image-missing"
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM1_MID
        
    def is_two_way(self):
        """
        Checks if we implement get() and put()

        DataSources can become two way datasources if they also override
        put() and set twoWayEnable to True
        """
        twoWay = hasattr(self, "put") and hasattr(self, "get")
        return twoWay

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
        logging.info("put() not overridden by derived class %s" % self.name)
                
    def get_num_items(self):
        """
        Returns the number of items requiring sychronization. This function 
        must be overridden by the appropriate dataprovider.
        @todo: Use this to make a progress dialog and does this number 
        represent the number of times that get shall be called??
        
        @returns: The number of items to synchronize
        @rtype: C{int}
        """
        logging.info("get_num_items() not overridden by derived class %s" % self.name)
        return NO_ITEMS

class DataSink(DataProviderBase):
    """
    Base Class for DataSinks
    """
    def __init__(self, name=None, description=None):
        """
        Sets the DataProvider color and a default icon
        """    
        #super fills in the name and description
        DataProviderBase.__init__(self, name, description)

        #customizations
        self.icon_name = "image-missing"
        self.widget_color_rgba = TANGO_COLOR_SKYBLUE_LIGHT

    def put(self, putData, onTopOf=None):
        """
        Stores data. The derived class is responsible for checking if putData
        conflicts. 
        
        In the case of a two-way datasource, the derived type should
        consider the onTopOf parameter, which if present, should provide the
        necesary information such that putData can replace (overwrite) it.

        @param putData: Data which to save
        @type putData: A L{conduit.DataType.DataType} derived type that this 
        dataprovider is capable of handling
        @param onTopOf: If this argument is not none, the dataprovider should
        ensure that putData replaces onTopOf (overwrites it). 
        @type onTopOf: A L{conduit.DataType.DataType} derived type that this 
        dataprovider is capable of handling        
        @raise: L{conduit.Exceptions.SynchronizeConflictError} if there is a
        conflict between the data being put, and that which it is overwriting
        """
        logging.info("put() not overridden by derived class %s" % self.name)

class DataProviderListModel(gtk.GenericTreeModel):
    """
    A listmodel for managing dynamically loaded modules. Manages an internal 
    list of L{conduit.ModuleManager.ModuleWrapper}
    
    @ivar modules: The array of modules under this treeviews control.
    @type modules: L{conduit.ModuleManager.ModuleWrapper}[]
    """
    COLUMN_TYPES = (gtk.gdk.Pixbuf, str, str, str, bool)
    COLUMN_NAMES = ['Name', 'Description']

    def __init__(self, module_wrapper_list):
        """
        TreeModel constructor
        
        Ignores modules which are not enabled
        """
        gtk.GenericTreeModel.__init__(self)
        #print "init, array= ", module_array
        #Only display 
        self.module_wrapper_list = [m for m in module_wrapper_list if m.enabled]
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
        return self.COLUMN_NAMES[:]

    def on_get_flags(self):
        """
        on_get_flags(
        """
        return gtk.TREE_MODEL_LIST_ONLY|gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        """
        on_get_n_columns(
        """
        return len(self.COLUMN_TYPES)

    def on_get_column_type(self, n):
        """
        on_get_column_type(
        """
        return self.COLUMN_TYPES[n]

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
        #Used internally from the TreeView to get the classname
        elif column is 3:
            return m.classname
        #Used internally from the TreeView to see if this is a category heading
        #and subsequently cancel the drag and drop
        elif column is 4:
            return False
        else:
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
 
class DataProviderTreeModel(gtk.GenericTreeModel):
    """
    A treemodel for managing dynamically loaded modules. Manages an internal 
    list of L{conduit.ModuleManager.ModuleWrapper}
    
    @todo: Make this display a tree
    @reference things by classname and not by name
    
    @ivar modules: The array of modules under this treeviews control.
    @type modules: L{conduit.ModuleManager.ModuleWrapper}[]
    """
    COLUMN_TYPES = (gtk.gdk.Pixbuf, str, str, str, bool)
    COLUMN_NAMES = ['Name', 'Description']

    def __init__(self, module_wrapper_list):
        """
        TreeModel constructor
        
        Ignores modules which are not enabled
        """
        gtk.GenericTreeModel.__init__(self)
        self.pathMappings = {}
        self.dataproviders = []
        self.cats = []
        
        #store a cache of loaded category icons for speed
        self.categoryIconCache = {}
        
        #Only display enabled modules
        module_wrapper_list = [m for m in module_wrapper_list if m.enabled]
        
        #Build a list of cats
        i = 0
        for mod in module_wrapper_list:
            if mod.category not in self.cats:
                self.cats.append(mod.category)
                #put into the path mappings
                self.pathMappings[mod.category] = (i,)
                i += 1

        #Put dp's of the same cat into different lists
        for cat in self.cats:
            #put each module in its own list
            listy = []
            for m in [x for x in module_wrapper_list if x.category == cat]:
                listy.append(m)
                #Store its path
                self.pathMappings[m] = (self.cats.index(cat),listy.index(m)) 
            self.dataproviders.append(listy)
           
        #for i in self.pathMappings:
        #    if isinstance(i,str):
        #        name = i
        #    else:
        #        name = i.name
        #    tup = self.pathMappings[i]
        #    logging.debug("Tree Model: %s : %s (%s)" % (name, tup, self.on_get_iter(tup,False)))
                

    def is_category_heading(self, rowref):
        return isinstance(rowref, str)
        
    def get_column_names(self):
        """
        get_column_names(
        """
        return self.COLUMN_NAMES[:]

    def on_get_flags(self):
        """
        on_get_flags(
        """
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        """
        on_get_n_columns(
        """
        return len(self.COLUMN_TYPES)

    def on_get_column_type(self, n):
        """
        on_get_column_type(
        """
        return self.COLUMN_TYPES[n]

    def on_get_iter(self, path, debug=False):
        """
        on_get_iter(
        """
        #Check if this is a toplevel row
        if len(path) == 1:
            if debug:
                print "on_get_iter: path = %s cat = %s" % (path, self.cats[path[0]])
            return self.cats[path[0]]
        else:
            try:
                if debug:
                    print "on_get_iter: path = %s dataprovider = %s" % (path, self.dataproviders[path[0]][path[1]])
                return self.dataproviders[path[0]][path[1]]
            except IndexError:
                #no modules loaded
                if debug:
                    print "on_get_iter: No modules loaded path = ", path
                return None

    def on_get_path(self, rowref):
        """
        on_get_path(
        """
        #print "on_get_path: rowref = ", rowref
        return self.pathMappings[rowref]

    def on_get_value(self, rowref, column):
        """
        on_get_value(
        """
        #print "on_get_value: rowref = %s column = %s" % (rowref, column)
        if column is 0:
            if self.is_category_heading(rowref):
                try:
                    #look to see if we have cached the icon
                    icon = self.categoryIconCache[rowref]
                except KeyError:
                    #not in cache, so load
                    try:
                        icon = gtk.icon_theme_get_default().load_icon(CATEGORY_ICONS[rowref], 16, 0)
                    except KeyError:
                        #dataprovider specified its own category so it gets a default icon
                        icon = gtk.icon_theme_get_default().load_icon("image-missing", 16, 0)
                    except gobject.GError:
                        #error loading fallback icon
                        icon = None
                    #store in cache for next time                        
                    self.categoryIconCache[rowref] = icon                      
                return icon
            else:
                return rowref.module.get_icon()
        elif column is 1:
            if self.is_category_heading(rowref):
                #For i8n we store some common translated category names
                try:
                    name = CATEGORY_NAMES[rowref]
                except KeyError:
                    name = rowref
                return name
            else:        
                return rowref.name
        elif column is 2:
            if self.is_category_heading(rowref):
                return None
            else:        
                return rowref.description
        #Used internally from the TreeView to get the classname
        elif column is 3:
            if self.is_category_heading(rowref):
                return "ImACategoryNotADataprovider"
            else:
                return rowref.classname
        #Used internally from the TreeView to see if this is a category heading
        #and subsequently cancel the drag and drop
        elif column is 4:        
            return self.is_category_heading(rowref)

    def on_iter_next(self, rowref):
        """
        on_iter_next(
        """
        path = self.pathMappings[rowref]
        try:
            #print "on_iter_next: current rowref = %s, path = %s" % (rowref, path)        
            #Check if its a toplevel row
            if len(path) == 1:
                return self.cats[path[0]+1]
            else:            
                return self.dataproviders[path[0]][path[1]+1] 
        except IndexError:
            #print "on_iter_next: index error iter next"
            return None
        
    def on_iter_children(self, rowref):
        """
        on_iter_children(
        """
        #print "on_iter_children: parent = ", rowref
        if rowref is None:
            return self.cats[0]
        else:
            path = self.pathMappings[rowref]
            #print "on_iter_children: children = ", self.dataproviders[path[0]][0]
            return self.dataproviders[path[0]][0]

    def on_iter_has_child(self, rowref):
        """
        on_iter_has_child(
        """
        #print "on_iter_has_child: rowref = %s, has child = %s" % (rowref,self.is_category_heading(rowref))
        return self.is_category_heading(rowref)

    def on_iter_n_children(self, rowref):
        """
        on_iter_n_children(
        """
        #print "on_iter_n_children: parent = ", rowref
        if rowref:
            path = self.pathMappings[rowref]
            return len(self.dataproviders[path[0]])
        return len(self.cats)

    def on_iter_nth_child(self, rowref, n):
        """
        on_iter_nth_child(
        """
        #print "on_iter_nth_child: rowref = %s n = %s" % (rowref, n)
        if rowref is None:
            return self.cats[n]
        else:
            path = self.pathMappings[rowref]
            try:
                return self.dataproviders[path[0]][n]
            except IndexError:
                return None
            

    def on_iter_parent(self, rowref):
        """
        on_iter_parent(
        """
        #print "on_iter_parent: child = ", rowref
        if self.is_category_heading(rowref):
            #print "on_iter_parent: parent = None"
            return None
        else:
            path = self.pathMappings[rowref.category]
            #print "on_iter_parent: parent = ", self.cats[path[0]]
            return self.cats[path[0]]
            
        
class DataProviderTreeView(gtk.TreeView):
    """
    Handles DND of DataProviders onto canvas
    """
    DND_TARGETS = [
    ('conduit/element-name', 0, 0)
    ]
    def __init__(self, model):
        """
        Constructor
        """
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
        #self.connect('drag-begin', self.on_drag_begin)
        self.connect('drag-data-get', self.on_drag_data_get)
        self.connect('drag-data-delete', self.on_drag_data_delete)
        
        #FIXME: Why does this cause it to hang??
        #gtk.TreeView.expand_all(self)
        
    def on_drag_begin(self, treeview, context):
        pass
        #treeselection = treeview.get_selection()
        #model, iter = treeselection.get_selected()
        #categoryHeading = model.get_value(iter, 4)
        #if categoryHeading:
        #    logging.debug("Aborting DND")
        #    context.drag_abort()
        

    def on_drag_data_get(self, treeview, context, selection, target_id, etime):
        """
        Get the data to be dropped by on_drag_data_received().
        We send the id of the dragged element.
        """
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        #get the classname
        data = model.get_value(iter, 3)
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
        
