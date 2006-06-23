import gtk
import gobject
import os
import sys
import traceback
import pydoc
from os.path import abspath, expanduser, join, basename

#WAS gsteditorelement
class ModuleLoader(gobject.GObject):
    """Generic dynamic module loader for conduit. Given a path
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
        """Converts a given array of directories into a list 
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
        """Tests whether the filename has the appropriate extension."""
        return (filename[-len(self.ext):] == self.ext)
        
    def _append_module(self, module):
        """Checks if the given module (checks by name) is already loaded
        into the modulelist array, if not it is added to that array
        """
        if module.name not in [i.name for i in self.loadedmodules]:
            self.loadedmodules.append(module)
        else:
            print >> sys.stderr, "module named %s allready loaded" % (module.name)
            
    def _import_module (self, filename):
        """Tries to import the specified file. Returns the python module on succes.
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
        """Loads all modules in the given file
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
        """Loads all modules
        """
  	
        for f in self.filelist:
            self.load_modules_in_file (f)

        #self.emit('modules-loaded')
        
    def get_modules (self, type_filter=None):
        """Returns all loaded modules of type specified by type_filter 
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
    """A generic wrapper for any dynamically loaded module
    """	
    def __init__ (self, name, description, module_type, category, module):
        self.name = name
        self.description = description        
        self.module_type = module_type
        self.category = category
        self.module = module
                   
import os, stat, time
import pygtk
pygtk.require('2.0')
import gtk

folderxpm = [
    "17 16 7 1",
    "  c #000000",
    ". c #808000",
    "X c yellow",
    "o c #808080",
    "O c #c0c0c0",
    "+ c white",
    "@ c None",
    "@@@@@@@@@@@@@@@@@",
    "@@@@@@@@@@@@@@@@@",
    "@@+XXXX.@@@@@@@@@",
    "@+OOOOOO.@@@@@@@@",
    "@+OXOXOXOXOXOXO. ",
    "@+XOXOXOXOXOXOX. ",
    "@+OXOXOXOXOXOXO. ",
    "@+XOXOXOXOXOXOX. ",
    "@+OXOXOXOXOXOXO. ",
    "@+XOXOXOXOXOXOX. ",
    "@+OXOXOXOXOXOXO. ",
    "@+XOXOXOXOXOXOX. ",
    "@+OOOOOOOOOOOOO. ",
    "@                ",
    "@@@@@@@@@@@@@@@@@",
    "@@@@@@@@@@@@@@@@@"
    ]
folderpb = gtk.gdk.pixbuf_new_from_xpm_data(folderxpm)

filexpm = [
    "12 12 3 1",
    "  c #000000",
    ". c #ffff04",
    "X c #b2c0dc",
    "X        XXX",
    "X ...... XXX",
    "X ......   X",
    "X .    ... X",
    "X ........ X",
    "X .   .... X",
    "X ........ X",
    "X .     .. X",
    "X ........ X",
    "X .     .. X",
    "X ........ X",
    "X          X"
    ]
filepb = gtk.gdk.pixbuf_new_from_xpm_data(filexpm)

class DataProviderTreeModel(gtk.GenericTreeModel):
    column_types = (str, str)
    column_names = ['Name', 'Description']

    def __init__(self, module_array):
        gtk.GenericTreeModel.__init__(self)
        print "init, array= ", module_array
        self.modules = module_array
        return 
        
    def get_module_index_by_name(self, name):
        print "get_module_index_by_name: name = ", name
        for n in range(0, len(self.modules)):
            if self.modules[n].name == name:
                return n
    
    def get_column_names(self):
        return self.column_names[:]

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY|gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_iter(self, path):
        print "on_get_iter: path =", path
        return self.modules[path[0]].name

    def on_get_path(self, rowref):
        print "on_get_path: rowref = ", rowref
        return self.modules[self.get_module_index_by_name(rowref)]

    def on_get_value(self, rowref, column):
        print "on_get_value: rowref = %s column = %s" % (rowref, column)
        m = self.modules[self.get_module_index_by_name(rowref)]
        if column is 0:
            return m.name
        elif column is 1:
            return m.description
        else:
            print "ERROR WILL ROBINSON"
            return None
        
    def on_iter_next(self, rowref):
        print "on_iter_next: rowref = ", rowref
        try:
            i = self.get_module_index_by_name(rowref)
            print "on_iter_next: old i = ", i
            i = i+1
            print "on_iter_next: next i = ", i
            return self.modules[i].name
        except IndexError:
            return None
        
    def on_iter_children(self, rowref):
        print "on_iter_children: rowref = ", rowref
        if rowref:
            return None
        return self.modules[0].name

    def on_iter_has_child(self, rowref):
        print "on_iter_has_child: rowref = ", rowref
        return False

    def on_iter_n_children(self, rowref):
        print "on_iter_n_children: rowref = ", rowref
        if rowref:
            return 0
        return len(self.modules)

    def on_iter_nth_child(self, rowref, n):
        print "on_iter_nth_chile: rowref = %s n = %s" % (rowref, n)
        if rowref:
            return None
        try:
            return self.modules[n].name
        except IndexError:
            return None

    def on_iter_parent(child):
        print "on_iter_parent: child = ", child
        return None
        
class DataProviderTreeModel2(gtk.GenericTreeModel):
    column_types = (gtk.gdk.Pixbuf, str, long, str, str)
    column_names = ['Name', 'Size', 'Mode', 'Last Changed']

    def __init__(self, dname=None):
        gtk.GenericTreeModel.__init__(self)
        if not dname:
            self.dirname = os.path.expanduser('~')
        else:
            self.dirname = os.path.abspath(dname)
        self.files = [f for f in os.listdir(self.dirname) if f[0] <> '.']
        self.files.sort()
        self.files = ['..'] + self.files
        return

    def get_pathname(self, path):
        filename = self.files[path[0]]
        return os.path.join(self.dirname, filename)

    def is_folder(self, path):
        filename = self.files[path[0]]
        pathname = os.path.join(self.dirname, filename)
        filestat = os.stat(pathname)
        if stat.S_ISDIR(filestat.st_mode):
            return True
        return False

    def get_column_names(self):
        return self.column_names[:]

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY|gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_iter(self, path):
        print "path ", path
        return self.files[path[0]]

    def on_get_path(self, rowref):
        return self.files.index(rowref)

    def on_get_value(self, rowref, column):
        print "rowref = ", rowref
        fname = os.path.join(self.dirname, rowref)
        try:
            filestat = os.stat(fname)
        except OSError:
            return None
        mode = filestat.st_mode
        if column is 0:
            if stat.S_ISDIR(mode):
                return folderpb
            else:
                return filepb
        elif column is 1:
            return rowref
        elif column is 2:
            return filestat.st_size
        elif column is 3:
            return oct(stat.S_IMODE(mode))
        return time.ctime(filestat.st_mtime)

    def on_iter_next(self, rowref):
        print "cheese = ", rowref
        try:
            i = self.files.index(rowref)+1
            return self.files[i]
        except IndexError:
            return None

    def on_iter_children(self, rowref):
        if rowref:
            return None
        return self.files[0]

    def on_iter_has_child(self, rowref):
        return False

    def on_iter_n_children(self, rowref):
        if rowref:
            return 0
        return len(self.files)

    def on_iter_nth_child(self, rowref, n):
        if rowref:
            return None
        try:
            return self.files[n]
        except IndexError:
            return None

    def on_iter_parent(child):
        return None        
