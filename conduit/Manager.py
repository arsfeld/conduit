import gtk
import gobject
import os
import sys
import traceback
import pydoc
from os.path import abspath, expanduser, join, basename

#WAS gsteditorelement
class Manager(gobject.GObject):
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
            if (mod.DATAPROVIDERS): pass
        except AttributeError:
            print >> sys.stderr, "The file %s is not a valid module. Skipping." %filename
            print >> sys.stderr, "A module must have the variable DATAPROVIDERS defined as a dictionary."
            traceback.print_exc()
            return

        if mod.DATAPROVIDERS == None:
            if not hasattr(mod, "ERROR"):
                mod.ERROR = "Unspecified Reason"

            print >> sys.stderr, "*** The file %s decided to not load itself: %s" % (filename, mod.ERROR)
            return

        for handler, infos in mod.DATAPROVIDERS.items():
            if hasattr(getattr(mod, handler), "initialize") and "name" in infos:
                pass				
            else:
                print >> sys.stderr, "Class %s in file %s does not have an initialize(self) method or does not define a 'name' attribute. Skipping." % (handler, filename)
                return

            if "requirements" in infos:
                status, msg, callback = infos["requirements"]()
                if status == deskbar.Handler.HANDLER_IS_NOT_APPLICABLE:
                    print >> sys.stderr, "***"
                    print >> sys.stderr, "*** The file %s (%s) decided to not load itself: %s" % (filename, handler, msg)
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

        for handler, infos in mod.DATAPROVIDERS.items():
        	print "Loading module '%s' from file %s." % (infos["name"], filename)
        	mod_instance = getattr (mod, handler) ()
        	#context = ModuleContext (mod_instance.get_icon(), False, mod_instance, filename, handler, infos)
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
