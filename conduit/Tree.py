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
from conduit.ModuleWrapper import ModuleWrapper
from conduit.Conflict import ArrowCellRenderer, LEFT_ARROW, RIGHT_ARROW, DOUBLE_ARROW, NO_ARROW

class CategoryWrapper(ModuleWrapper):
    """
    Represents a category stored in the treemodel. Not generally intended 
    to be used outside of C{conduit.Tree.DataProviderTreeModel}
    """
    def __init__(self, category):
        ModuleWrapper.__init__(
                            self,
                            category.name,  #name: shows in name column
                            None,           #description: shows in description column
                            category.icon,  #icon name
                            "category",     #module_type: used to cancel drag and drop
                            category,       #category: untranslated version on Name 
                            None,           #in_type: N/A
                            None,           #out_type: N/A
                            None,           #classname: N/A
                            (),             #initargs: N/A
                            category,       #object instance: N/A
                            True)           #enabled: True but N/A

       
class DataProviderTreeModel(gtk.GenericTreeModel):
    """
    A treemodel for managing dynamically loaded modules. Manages an internal 
    list of L{conduit.ModuleManager.ModuleWrapper}
    
    @ivar modules: The array of modules under this treeviews control.
    @type modules: L{conduit.ModuleManager.ModuleWrapper}[]
    """
    COLUMN_TYPES = (gtk.gdk.Pixbuf, str, str, str, bool, str)

    def __init__(self, module_wrapper_list=[]):
        """
        TreeModel constructor
        
        Ignores modules which are not enabled
        """
        gtk.GenericTreeModel.__init__(self)
        #A dictionary mapping wrappers to paths
        self.pathMappings = {}
        #2D array of wrappers at their path indexes
        self.dataproviders = []
        #Array of wrappers at their path indexes
        self.cats = []

        #Add dataproviders
        self.add_dataproviders(module_wrapper_list)
        
    def _is_category_heading(self, rowref):
        return rowref.module_type == "category"

    def _get_category_index_by_name(self, category_name):
        i = 0
        for j in self.cats:
            if j.category == category_name:
                return i
            i += 1
        return None

    def _get_category_by_name(self, category_name):
        idx = self._get_category_index_by_name(category_name)
        return self.cats[idx]

    def add_dataproviders(self, dpw=[]):
        """
        Adds all enabled dataproviders to the model
        """
        #Only display enabled modules
        module_wrapper_list = [m for m in dpw if m.enabled]
        
        #Add them to the module
        for mod in module_wrapper_list:
            self.add_dataprovider(mod, True)
                
    def add_dataprovider(self, dpw, signal=True):
        """
        Adds a dataprovider to the model. Creating a category for it if
        it does not exist

        @param dpw: The dataproviderwrapper to add
        @param signal: Whether the associated treeview should be signaled to
        update the GUI. Set to False for the first time the model is 
        built (in the constructor)
        @type signal: C{bool}
        """
        logging.debug("Adding DataProvider %s to TreeModel" % dpw)
        #Do we need to create a category first?
        i = self._get_category_index_by_name(dpw.category)
        if i == None:
            logging.debug("Creating Category %s" % dpw.category)
            new_cat = CategoryWrapper(dpw.category)
            self.cats.append(new_cat)
            i = self.cats.index(new_cat)
            self.pathMappings[new_cat] = (i,)
            #Signal the treeview to redraw
            if signal:
                path=self.on_get_path(new_cat)
                self.row_inserted(path, self.get_iter(path))

        #Now add the dataprovider to the categories children
        try:
            self.dataproviders[i].append(dpw)
        except IndexError:
            #Doesnt have any kids... yet!
            self.dataproviders.insert(i, [dpw])

        #Store the index            
        j = self.dataproviders[i].index(dpw)
        self.pathMappings[dpw] = (i,j)
        
        #Signal the treeview to redraw
        if signal:
            path=self.on_get_path(dpw)
            self.row_inserted(path, self.get_iter(path))

    def remove_dataprovider(self, dpw, signal=True):
        """
        Removes the dataprovider from the treemodel. Also removes the
        category that it was in if there is no remaining dataproviders in
        that category
        """
        pass
        #self.row_deleted(path)
        #del (self.childrencache[parent])

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
        if len(self.cats) == 0:
            return None            
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
        path = self.pathMappings[rowref]
        #print "PATH = ", path
        return path

    def on_get_value(self, rowref, column):
        """
        on_get_value(
        """
        #print "on_get_value: rowref = %s column = %s" % (rowref, column)
        if column is 0:
            return rowref.get_icon()
        elif column is 1:
            return rowref.name
        elif column is 2:
            return rowref.description
        #Used internally from the TreeView to get the key used by the canvas to 
        #reinstantiate new dataproviders
        elif column is 3:
            if self._is_category_heading(rowref):
                return "ImACategoryNotADataprovider"
            else:
                return rowref.get_key()
        #Used internally from the TreeView to see if this is a category heading
        #and subsequently cancel the drag and drop
        elif column is 4:        
            return self._is_category_heading(rowref)
        elif column is 5:
            return rowref.module_type

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
        #print "on_iter_has_child: rowref = %s, has child = %s" % (rowref,self._is_category_heading(rowref))
        return self._is_category_heading(rowref)

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
        if self._is_category_heading(rowref):
            #print "on_iter_parent: parent = None"
            return None
        else:
            cat = self._get_category_by_name(rowref.category)
            path = self.on_get_path(cat)
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
        
        # First column is an image and the name...
        pixbufRenderer = gtk.CellRendererPixbuf()
        textRenderer = gtk.CellRendererText()
        tvcolumn0 = gtk.TreeViewColumn("Name", pixbufRenderer, pixbuf=0)
        tvcolumn0.pack_start(textRenderer, False)
        tvcolumn0.add_attribute(textRenderer, 'text', 1)
        self.append_column(tvcolumn0)

        # Second cell is a gammy arrow indicating source or sink and a description
        arrowRenderer = ArrowCellRenderer()
        textRenderer = gtk.CellRendererText()
        tvcolumn1 = gtk.TreeViewColumn("Description", arrowRenderer)
        tvcolumn1.set_cell_data_func(arrowRenderer, self.set_direction_func)
        tvcolumn1.pack_start(textRenderer, False)
        tvcolumn1.add_attribute(textRenderer, 'text', 2)
        self.append_column(tvcolumn1)

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

    def expand_all(self):
        #FIXME: This used to cause the GUI to hang. Now it doesnt... curious
        gtk.TreeView.expand_all(self)
        
    def on_drag_begin(self, treeview, context):
        pass
        #treeselection = treeview.get_selection()
        #model, iter = treeselection.get_selected()
        #categoryHeading = model.get_value(iter, 4)
        #if categoryHeading:
        #    logging.debug("Aborting DND")
        #    context.drag_abort()

    def set_direction_func(self, column, cell_renderer, tree_model, iter):
        module_type = tree_model.get_value(iter, 5)
        if module_type == "source":
            cell_renderer.set_direction(RIGHT_ARROW)
        elif module_type == "sink":
            cell_renderer.set_direction(LEFT_ARROW)
        elif module_type == "twoway":
            cell_renderer.set_direction(DOUBLE_ARROW)
        else:
            cell_renderer.set_direction(NO_ARROW)

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
        
    def get_expanded_rows(self):
        def map_expanded_rows_func(treeview, path):
            expanded.append(path)

        expanded = []
        self.map_expanded_rows(map_expanded_rows_func)
        return expanded
