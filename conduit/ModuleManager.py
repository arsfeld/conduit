import gtk
import gobject
import os
import sys
import traceback
import pydoc
from os.path import abspath, expanduser, join, basename

class ModuleManager(gobject.GObject):
    """
    Manager Class for ALL dynamically loaded modules.
    Generated treeview and treestore representations of the
    loaded modules and can instanciate new ones. 
    Applications should use this class and its methods rather 
    than the ModuleLoader, TreeStore and TreeView classes directly 
    """
    
    def __init__(self, dirs=None):
        """
		dirs: A list of directories to search. Relative pathnames and paths
			  containing ~ will be expanded. If dirs is None the 
			  ModuleLoader will not search for modules.
		"""
        gobject.GObject.__init__(self)        
        self.module_loader = ModuleLoader(dirs)
        self.module_loader.load_all_modules()
                
    def get_module(self, name=None, category=None):
        """
        Returns a Module (not a ModuleWrapper) specified by name
        """
        print "SEARCHING Category = %s Name = %s" % (name, category)
        mods = self.module_loader.get_modules(category)
        for m in mods:
            if name == m.name:
                print "FOUND name = ", name
                return m
                
    def get_module_do_copy(self, name=None, category=None):
        """
        Returns a copy of a Module (not a ModuleWrapper)
        """
        print "not implemented"
        
    def get_treeview(self, category=None):
        """
        Returns a treeview (for displaying a list of ModuleContexts)
        in the specified category.
        """
        tm = self._get_treemodel(category)
        return DataProviderTreeView(tm)
                
    def _get_treemodel(self, category=None):
        """
        Returns a treemodel containing  the ModuleContexts
        in the specified category
        """
        mods = self.module_loader.get_modules(category)
        tm = DataProviderTreeModel(mods)
        return tm

#WAS gsteditorelement
class ModuleLoader(gobject.GObject):
    """
    Generic dynamic module loader for conduit. Given a path
    it loads all modules in that directory, keeping them in an
    internam array which may be returned via get_modules
    """
       
    def __init__(self, dirs=None, extension=".py"):
        """
		dirs: A list of directories to search. Relative pathnames and paths
			  containing ~ will be expanded. If dirs is None the 
			  ModuleLoader will not search for modules.
		extension: What extension should this ModuleLoader accept (string).
		"""
        gobject.GObject.__init__(self)

        self.ext = extension
        self.filelist = self._build_filelist_from_directories (dirs)
        self.loadedmodules = [] 
            
    def _build_filelist_from_directories (self, directories=None):
        """
        Converts a given array of directories into a list 
        containing the filenames of all qualified modules.
        This method is automatically invoked by the constructor.
        """
        res = []
        if not directories:
            return res
            
        #convert to abs path    
        directories = [abspath(expanduser(s)) for s in directories]
            
        for d in directories:
        	#print >> sys.stderr, "Reading directory %s" % d
        	try:
        		if not os.path.exists(d):
        			continue

        		for i in [join(d, m) for m in os.listdir (d) if self._is_module(m)]:
        			if basename(i) not in [basename(j) for j in res]:
        				res.append(i)
        	except OSError, err:
        		print >> sys.stderr, "Error reading directory %s, skipping." % d
        		traceback.print_exc()
        return res			
       
    def _is_module (self, filename):
        """
        Tests whether the filename has the appropriate extension.
        """
        return (filename[-len(self.ext):] == self.ext)
        
    def _append_module(self, module):
        """
        Checks if the given module (checks by name) is already loaded
        into the modulelist array, if not it is added to that array
        """
        if module.name not in [i.name for i in self.loadedmodules]:
            self.loadedmodules.append(module)
        else:
            print >> sys.stderr, "module named %s allready loaded" % (module.name)
            
    def _import_module (self, filename):
        """
        Tries to import the specified file. Returns the python module on succes.
        Primarily for internal use. Note that the python module returned may actually
        contain several more loadable modules.
        """
        try:
            mod = pydoc.importfile (filename)
        except Exception:
            print >> sys.stderr, "Error loading the file: %s." % filename
            traceback.print_exc()
            return

        try:
            if (mod.MODULES): pass
        except AttributeError:
            print >> sys.stderr, "The file %s is not a valid module. Skipping." %filename
            print >> sys.stderr, "A module must have the variable MODULES defined as a dictionary."
            traceback.print_exc()
            return

        if mod.MODULES == None:
            if not hasattr(mod, "ERROR"):
                mod.ERROR = "Unspecified Reason"

            print >> sys.stderr, "*** The file %s decided to not load itself: %s" % (filename, mod.ERROR)
            return

        for modules, infos in mod.MODULES.items():
            if hasattr(getattr(mod, modules), "initialize") and "name" in infos:
                pass				
            else:
                print >> sys.stderr, "Class %s in file %s does not have an initialize(self) method or does not define a 'name' attribute. Skipping." % (modules, filename)
                return

            if "requirements" in infos:
                status, msg, callback = infos["requirements"]()
                if status == deskbar.Handler.HANDLER_IS_NOT_APPLICABLE:
                    print >> sys.stderr, "*** The file %s (%s) decided to not load itself: %s" % (filename, modules, msg)
                    return

        return mod
        
    def load_modules_in_file (self, filename):
        """
        Loads all modules in the given file
        """
        mod = self._import_module (filename)
        if mod is None:
        	return

        for modules, infos in mod.MODULES.items():
        	#print "Loading module '%s' from file %s." % (infos["name"], filename)
        	mod_instance = getattr (mod, modules) ()
        	mod_wrapper = ModuleWrapper (infos["name"], infos["description"], infos["type"], infos["category"], mod_instance)
        	self._append_module(mod_wrapper)
            #self.emit("module-loaded", context)
            
    def load_all_modules (self):
        """
        Loads all modules
        """
  	
        for f in self.filelist:
            self.load_modules_in_file (f)

        #self.emit('modules-loaded')
        
    def get_modules (self, type_filter=None):
        """
        Returns all loaded modules of type specified by type_filter 
        or all if the filter is set to None.
        """
        if type_filter is None:
            return self.loadedmodules
        else:
            mods = []
            for i in self.loadedmodules:
                if i.module_type == type_filter:
                    mods.append(i)
            
            return mods        
            
        
class ModuleWrapper(gobject.GObject): 
    """
    A generic wrapper for any dynamically loaded module
    """	
    def __init__ (self, name, description, module_type, category, module):
        self.name = name
        self.description = description        
        self.module_type = module_type
        self.category = category
        self.module = module
                   
class DataProviderTreeModel(gtk.GenericTreeModel):
    column_types = (gtk.gdk.Pixbuf, str, str)
    column_names = ['Pic', 'Name', 'Description']

    def __init__(self, module_array):
        gtk.GenericTreeModel.__init__(self)
        #print "init, array= ", module_array
        self.modules = module_array
        return 
        
    def get_module_index_by_name(self, name):
        #print "get_module_index_by_name: name = ", name
        for n in range(0, len(self.modules)):
            if self.modules[n].name == name:
                return n
                
    def get_module_by_name(self, name):
        #TODO: ERROR CHECK
        return self.modules[self.get_module_index_by_name(name)]
    
    def get_column_names(self):
        return self.column_names[:]

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY|gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_iter(self, path):
        #print "on_get_iter: path =", path
        return self.modules[path[0]].name

    def on_get_path(self, rowref):
        #print "on_get_path: rowref = ", rowref
        return self.modules[self.get_module_index_by_name(rowref)]

    def on_get_value(self, rowref, column):
        #print "on_get_value: rowref = %s column = %s" % (rowref, column)
        m = self.modules[self.get_module_index_by_name(rowref)]
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
        #print "on_iter_next: rowref = ", rowref
        try:
            i = self.get_module_index_by_name(rowref)
            #print "on_iter_next: old i = ", i
            i = i+1
            #print "on_iter_next: next i = ", i
            return self.modules[i].name
        except IndexError:
            return None
        
    def on_iter_children(self, rowref):
        #print "on_iter_children: rowref = ", rowref
        if rowref:
            return None
        return self.modules[0].name

    def on_iter_has_child(self, rowref):
        #print "on_iter_has_child: rowref = ", rowref
        return False

    def on_iter_n_children(self, rowref):
        #print "on_iter_n_children: rowref = ", rowref
        if rowref:
            return 0
        return len(self.modules)

    def on_iter_nth_child(self, rowref, n):
        #print "on_iter_nth_chile: rowref = %s n = %s" % (rowref, n)
        if rowref:
            return None
        try:
            return self.modules[n].name
        except IndexError:
            return None

    def on_iter_parent(child):
        #print "on_iter_parent: child = ", child
        return None
        
class DataProviderTreeView(gtk.TreeView):
    DND_TARGETS = [
    #('STRING', 0, 0),
    #('text/plain', 0, 1),
    ('conduit/element-name', 0, 2)
    ]
    def __init__(self, model):
        gtk.TreeView.__init__(self, model)
        
        column_names = model.get_column_names()
        tvcolumn = [None] * len(column_names)
        # First cell in the column is for an image...
        tvcolumn[0] = gtk.TreeViewColumn(column_names[0], gtk.CellRendererPixbuf(), pixbuf=0)
        self.append_column(tvcolumn[0])
        # Second cell is name
        tvcolumn[1] = gtk.TreeViewColumn(column_names[1], gtk.CellRendererText(), text=1)
        self.append_column(tvcolumn[1])
        # Third cell is description
        tvcolumn[2] = gtk.TreeViewColumn(column_names[2], gtk.CellRendererText(), text=2)
        self.append_column(tvcolumn[2])
        
        # DND info:
        # drag
        self.enable_model_drag_source(  gtk.gdk.BUTTON1_MASK,
                                        #[DataProviderTreeView.DND_TARGETS[-1]],
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
