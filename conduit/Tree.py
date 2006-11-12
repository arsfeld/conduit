"""
Cotains treeview and treemodel classes for displaying the 
dataproviders

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
import conduit.DataProvider as DataProvider

#Store the translated catgory names
CATEGORY_NAMES = {
    DataProvider.CATEGORY_LOCAL : _("On This Computer"),
    DataProvider.CATEGORY_WEB : _("On The Web"),
    DataProvider.CATEGORY_GOOGLE : _("Google")
    }

#Icon names for each category
CATEGORY_ICONS = {
    DataProvider.CATEGORY_LOCAL : "computer",
    DataProvider.CATEGORY_WEB : "applications-internet",
    DataProvider.CATEGORY_GOOGLE : "applications-internet"
    } 

ICON_IDX = 0
NAME_IDX = 1
DESCRIPTION_IDX = 2
CLASSNAME_IDX = 3
IS_HEADING_IDX = 4
class Thingee:
    """
    Light wrapper class to store information about dataproviders stored in the
    DataProvider tree model.
    """
    def __init__(self, name, icon, description, classname=None, category=None, flags={}):
        self.name = name
        self.icon = icon
        self.description = description
        self.classname = classname
        self.category = category
        self.flags = flags

    @staticmethod
    def new_from_dataprovider(dataproviderWrapper):
        return Thingee(
            dataproviderWrapper.name,
            dataproviderWrapper.module.get_icon(),
            dataproviderWrapper.description,
            dataproviderWrapper.classname,
            dataproviderWrapper.category
            )

    @staticmethod
    def new_from_category(categoryName):
        return Thingee(
            categoryName,
            None,
            None,
            None,
            None
            )

    #This class is accessed like a list by the treeview
    def __getitem__(self, i):
        if i == ICON_IDX:
            pass
        elif i == NAME_IDX:
            pass
        elif i == DESCRIPTION_IDX:
            pass
        elif i == CLASSNAME_IDX:
            pass
        elif i == IS_HEADING_IDX:
            pass
        else:
            pass

    def __str__(self):
        return "Classname=%s" % self.classname
        
    def is_category(self):
        return self.classname == None

    def in_category(self, categoryName):
        return self.category == categoryName

    def get_flag(self, key):
        if not self.flags.has_key(key):
            return None
        else:
            return self.flags[key]

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
        path = self.on_get_path(rowref)
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
            path = self.on_get_path(rowref)
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
            path = self.on_get_path(rowref)
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
            path = self.on_get_path(rowref)
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
            path = self.on_get_path(rowref.category)
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
        
