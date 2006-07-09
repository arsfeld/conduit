import gtk
import gobject
import os
import sys
import traceback
import pydoc
import random
from os.path import abspath, expanduser, join, basename

import logging
import conduit
import conduit.DataProvider as DataProvider


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
        Constructor for ModuleManger.
        
		@param dirs: A list of directories to search. Relative pathnames and 
		paths containing ~ will be expanded. If dirs is None the 
		ModuleLoader will not search for modules.
		@type dirs: C{string[]}
		"""
        gobject.GObject.__init__(self)        
        self.module_loader = ModuleLoader(dirs)
        self.module_loader.load_all_modules()
                
    def get_module(self, name=None, type_filter=None):
        """
        Returns a Module (not a ModuleWrapper) specified by name
        
        @param name: Name of the module to get
        @type name: C{string}
        @param type_filter: An option string which restrickts the search
        to modules of a specified type. For example, to only search for
        L{conduit.DataProvider.DataSink} specify "sink" here.
        @type type_filter: C{string}
        @rtype: a L{conduit.ModuleManager}
        @returns: cheese
        """
        logging.info("SEARCHING Type = %s Name = %s" % (type_filter, name))
        mods = self.module_loader.get_modules(type_filter)
        for m in mods:
            if name == m.name:
                logging.info("FOUND name = %s" % (name))
                return m
                
    def get_module_do_copy(self, name=None, type_filter=None):
        """
        Returns a copy of a Module (not a ModuleWrapper)
        """
        print "not implemented"
        
    def get_treeview(self, type_filter=None):
        """
        Returns a treeview (for displaying a list of ModuleContexts)
        of the specified type.
        """
        tm = self._get_treemodel(type_filter)
        return DataProvider.DataProviderTreeView(tm)
                
    def _get_treemodel(self, type_filter=None):
        """
        Returns a treemodel containing  the ModuleContexts
        of the specified type
        """
        mods = self.module_loader.get_modules(type_filter)
        tm = DataProvider.DataProviderTreeModel(mods)
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
		@param dirs: A list of directories to search. Relative pathnames and paths
		containing ~ will be expanded. If dirs is None the 
		ModuleLoader will not search for modules.
		@type dirs: C{string[]}
		@param extension: What extension should this ModuleLoader accept (string).
		@type extension: C{string}
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
        	logging.info("Reading directory %s" % d)
        	try:
        		if not os.path.exists(d):
        			continue

        		for i in [join(d, m) for m in os.listdir (d) if self._is_module(m)]:
        			if basename(i) not in [basename(j) for j in res]:
        				res.append(i)
        	except OSError, err:
        		logging.warn("Error reading directory %s, skipping." % (d))
        		#traceback.print_exc()
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
        
        @param module: The module to append.
        @type module: L{conduit.ModuleManager.ModuleWrapper}
        """
        if module.name not in [i.name for i in self.loadedmodules]:
            self.loadedmodules.append(module)
        else:
            logging.warn("module named %s allready loaded" % (module.name))
            
    def _import_module (self, filename):
        """
        Tries to import the specified file. Returns the python module on succes.
        Primarily for internal use. Note that the python module returned may actually
        contain several more loadable modules.
        """
        try:
            mod = pydoc.importfile (filename)
        except Exception:
            logging.error("Error loading the file: %s." % (filename))
            traceback.print_exc()
            return

        try:
            if (mod.MODULES): pass
        except AttributeError:
            logging.error("The file %s is not a valid module. Skipping." % (filename))
            logging.error("A module must have the variable MODULES defined as a dictionary.")
            traceback.print_exc()
            return

        if mod.MODULES == None:
            if not hasattr(mod, "ERROR"):
                mod.ERROR = "Unspecified Reason"

            logging.error("*** The file %s decided to not load itself: %s" % (filename, mod.ERROR))
            return

        for modules, infos in mod.MODULES.items():
            if hasattr(getattr(mod, modules), "initialize") and "name" in infos:
                pass				
            else:
                logging.error("Class %s in file %s does not have an initialize(self) method or does not define a 'name' attribute. Skipping." % (modules, filename))
                return

            if "requirements" in infos:
                status, msg, callback = infos["requirements"]()
                if status == deskbar.Handler.HANDLER_IS_NOT_APPLICABLE:
                    logging.error("*** The file %s (%s) decided to not load itself: %s" % (filename, modules, msg))
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
        	mod_wrapper = ModuleWrapper (  infos["name"], 
        	                               infos["description"], 
        	                               infos["type"], 
        	                               infos["category"], 
        	                               infos["in_type"],
        	                               infos["out_type"],
        	                               mod_instance)
        	self._append_module(mod_wrapper)
            #self.emit("module-loaded", context)
            
    def load_all_modules (self):
        """
        Loads all modules stored in the current directory
        """
  	
        for f in self.filelist:
            self.load_modules_in_file (f)

        #self.emit('modules-loaded')
        
    def get_modules (self, type_filter=None):
        """
        Returns all loaded modules of type specified by type_filter 
        or all if the filter is set to None.
        
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        @returns: A list of L{conduit.ModuleManager.ModuleWrapper}
        """
        if type_filter is None:
            return self.loadedmodules
        else:
            mods = []
            for i in self.loadedmodules:
                if i.module_type == type_filter:
                    mods.append(i)
            
            return mods        
            
#Number of digits in the module UID string        
UID_DIGITS = 5

class ModuleWrapper(gobject.GObject): 
    """
    A generic wrapper for any dynamically loaded module. Wraps the complexity
    of a stored L{conduit.DataProvider.DataProvider} behind additional
    descriptive fields like name and description. Useful for classification 
    and searching for moldules of certain types, etc.
    
    @ivar name: The name of the contained module
    @type name: C{string}
    @ivar description: The description of the contained module
    @type description: C{string}
    @ivar module_type: The type of the contained module (e.g. sink, source)
    @type module_type: C{string}
    @ivar category: The category of the contained module
    @type category: C{string}
    @ivar module: The name of the contained module
    @type module: L{conduit.DataProvider.DataProvider}, 
    L{conduit.DataType.DataType} or derived class     
    @ivar uid: A Unique identifier for the module
    @type uid: C{string}
    """	
    def __init__ (self, name, description, module_type, category, in_type, out_type, module, uid=None):
        """
        Constructor for ModuleWrapper. A convenient wrapper around a dynamically
        loaded module.
        
        @param name: The name of the contained module
        @type name: C{string}
        @param description: The description of the contained module
        @type description: C{string}
        @param module_type: The type of the contained module (e.g. sink, source)
        @type module_type: C{string}
        @param category: The category of the contained module
        @type category: C{string}
        @param module: The name of the contained module
        @type module: L{conduit.DataProvider.DataProvider} or derived class     
        @param uid: (optional) A Unique identifier for the module. This should be s
        specified if, for example, we are recreating a previously stored sync set
        @type uid: C{string}
        """
        gobject.GObject.__init__(self)
                
        self.name = name
        self.description = description        
        self.module_type = module_type
        self.category = category
        self.module = module
        self.in_type = in_type
        self.out_type = out_type
        if uid is None:
            self.uid = str(random.randint(0,10**UID_DIGITS))
            
    def get_icon(self):
        """
        Gets the icon for the contained module. A bit hackish because I could
        not work out how to derive the dynamically loaded modules from this
        type. If the contained module is not a source or a sink then
        return None for the icon
        """
        if self.module is not None:
            if isinstance(self.module, conduit.DataProvider.DataProviderBase):
                return self.module.get_icon()
        
        return None
