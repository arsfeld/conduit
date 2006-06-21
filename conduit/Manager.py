import gtk
import gobject
import os
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
        else:
            self.dirs = None
            self.filelist = []

    def build_filelist (self):
        """Returns a list containing the filenames of all qualified modules.
        This method is automatically invoked by the constructor.
        """
        res = []
        for d in self.dirs:
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
