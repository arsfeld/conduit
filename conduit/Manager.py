import gtk
import gobject
import os
import sys
import traceback
import pydoc
from os.path import abspath, expanduser, join, basename

#WAS gsteditorelement
class ModuleLoader(gobject.GObject):
    "Manages all DataSinks and DataSources in the Application"
    
    def __init__(self, dirs=None, extension=".py"):
        """
		dirs: A list of directories to search. Relative pathnames and paths
			  containing ~ will be expanded. If dirs is None the 
			  ModuleLoader will not search for modules.
		extension: What extension should this ModuleLoader accept (string).
		"""
        gobject.GObject.__init__(self)
        #TODO: Scan paths for valid objects
        self.ext = extension
		
        if (dirs):
            self.dirs = [abspath(expanduser(s)) for s in dirs]
            self.filelist = self.build_filelist ()
            print self.filelist
        else:
            self.dirs = None
            self.filelist = []
            
        self.loadedmodules = [] 
            
    def build_filelist (self):
        """Returns a list containing the filenames of all qualified modules.
        This method is automatically invoked by the constructor.
        """
        res = []
        for d in self.dirs:
        	print >> sys.stderr, "Reading directory %s" % d
        	try:
        		if not os.path.exists(d):
        			continue

        		for i in [join(d, m) for m in os.listdir (d) if self.is_module(m)]:
        			if basename(i) not in [basename(j) for j in res]:
        				res.append(i)
        	except OSError, err:
        		print >> sys.stderr, "Error reading directory %s, skipping." % d
        		traceback.print_exc()
        return res			
       
    def is_module (self, filename):
        """Tests whether the filename has the appropriate extension."""
        return (filename[-len(self.ext):] == self.ext)
            
    def import_module (self, filename):
        """Tries to import the specified file. Returns the python module on succes.
        Primarily for internal use."""
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
                    print >> sys.stderr, "***"
                    print >> sys.stderr, "*** The file %s (%s) decided to not load itself: %s" % (filename, modules, msg)
                    print >> sys.stderr, "***"
                    return

        return mod
        
    def load (self, filename):
        """Loads the given file as a module and emits a 'module-loaded' signal
        passing a corresponding ModuleContext as argument.
        """
        mod = self.import_module (filename)
        if mod is None:
        	return

        for modules, infos in mod.MODULES.items():
        	print "Loading module '%s' from file %s." % (infos["name"], filename)
        	mod_instance = getattr (mod, modules) ()
        	context = ModuleWrapper (infos["name"], infos["description"], infos["type"], mod_instance)
        	self.loadedmodules.append(context)
            #self.emit("module-loaded", context)
            
    def load_all (self):
        """Tries to load all qualified modules detected by the ModuleLoader.
        Each time a module is loaded it will emit a 'module-loaded' signal
        passing a corresponding module context.
        """
        if self.dirs is None:
            print >> sys.stderr, "The ModuleLoader at %s has no filelist!" % str(id(self))
            print >> sys.stderr, "It was probably initialized with dirs=None."
            return
    	
        for f in self.filelist:
            self.load (f)

        #self.emit('modules-loaded') 
        
class ModuleWrapper(gobject.GObject): 
    """A generic wrapper for any dynamically loaded module
    """	
    def __init__ (self, name, description, module_type, module):
        self.name = name
        self.description = description        
        self.module_type = module_type
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
        return self.files[path[0]]

    def on_get_path(self, rowref):
        return self.files.index(rowref)

    def on_get_value(self, rowref, column):
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
