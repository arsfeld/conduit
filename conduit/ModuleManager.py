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
                
    def get_module(self, name):
        """
        Returns a ModuleWrapper specified by name
        """
        return self.module_loader.get_module_named(name)
                
    def get_module_do_copy(self, name):
        """
        Returns a copy of a ModuleWrapper
        """
        return self.module_loader.get_new_instance_module_named(name)

        
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
        self.filelist = self.build_filelist_from_directories (dirs)
        self.loadedmodules = [] 
            
    def build_filelist_from_directories(self, directories=None):
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

        		for i in [join(d, m) for m in os.listdir (d) if self.is_module(m)]:
        			if basename(i) not in [basename(j) for j in res]:
        				res.append(i)
        	except OSError, err:
        		logging.warn("Error reading directory %s, skipping." % (d))
        		#traceback.print_exc()
        return res			
       
    def is_module(self, filename):
        """
        Tests whether the filename has the appropriate extension.
        """
        return (filename[-len(self.ext):] == self.ext)
        
    def append_module(self, module):
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
            
    def import_file(self, filename):
        """
        Tries to import the specified file. Returns the python module on succes.
        Primarily for internal use. Note that the python module returned may actually
        contain several more loadable modules.
        """
        try:
            mods = pydoc.importfile (filename)
        except Exception:
            logging.error("Error loading the file: %s." % (filename))
            traceback.print_exc()
            return

        try:
            if (mods.MODULES): pass
        except AttributeError:
            logging.error("The file %s is not a valid module. Skipping." % (filename))
            logging.error("A module must have the variable MODULES defined as a dictionary.")
            return

        for modules, infos in mods.MODULES.items():
            for i in ModuleWrapper.COMPULSORY_ATTRIBUTES:
                if i not in infos:
                    logging.error("Class %s in file %s does define a %s attribute. Skipping." % (modules, filename, i))
                    return

        return mods
        
    def load_modules_in_file (self, filename):
        """
        Loads all modules in the given file
        """
        mod = self.import_file(filename)
        if mod is None:
        	return

        for modules, infos in mod.MODULES.items():
            mod_instance = getattr (mod, modules) ()
            mod_wrapper = ModuleWrapper (  infos["name"], 
        	                               infos["description"], 
        	                               infos["type"], 
        	                               infos["category"], 
        	                               infos["in_type"],
        	                               infos["out_type"],
        	                               str(modules),
        	                               filename,
        	                               mod_instance)
            self.append_module(mod_wrapper)
            #self.emit("module-loaded", context)
            
    def load_all_modules(self):
        """
        Loads all modules stored in the current directory
        """
        for f in self.filelist:
            self.load_modules_in_file (f)
        
    def get_all_modules(self):
        return self.loadedmodules
        
    def get_modules_by_type(self, type_filter):
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
            
    def get_module_named(self, name):
        """
        Returns a Module (not a ModuleWrapper) specified by name
        
        @param name: Name of the module to get
        @type name: C{string}
        @returns: An already instanciated ModuleWrapper
        @rtype: a L{conduit.ModuleManager.ModuleWrapper}
        """
        logging.info("Searching for module named %s" % (name))
        for m in self.loadedmodules:
            if name == m.name:
                logging.info("Returning module named %s" % (name))
                return m
                
        logging.warn("Could not find module named %s" % (name))
        return None
                
    def get_new_instance_module_named(self, name):
        logging.info("Searching for module named %s" % (name))
        #check if its loaded (i.e. been checked and is instanciatable)
        if name in [i.name for i in self.loadedmodules]:
            for m in self.loadedmodules:
                if name == m.name:
                    #reimport the file that the module was in
                    mods = self.import_file(m.filename)
                    #re-instanciate it
                    mod_instance = getattr (mods, m.classname) ()
                    #put it into a new wrapper
                    mod_wrapper = ModuleWrapper(  
                                               m.name, 
            	                               m.description, 
            	                               m.module_type, 
            	                               m.category, 
            	                               m.in_type,
            	                               m.out_type,
            	                               m.classname,
            	                               m.filename,
            	                               mod_instance)
                    
                    logging.info("Returning new instance of module named %s" % (m.name))
                    return mod_wrapper
        #Didnt load at app startup so its not gunna load now!
        return None
            
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
    
    NUM_UID_DIGITS = 5
    COMPULSORY_ATTRIBUTES = [
                            "name",
                            "description",
                            "type",
                            "category",
                            "in_type",
                            "out_type"
                            ]
    	
    def __init__ (self, name, description, module_type, category, in_type, out_type, classname, filename, module):
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
        @param classname: The classname used to instanciate another
        modulewrapper of type C{module} contained in C{filename}
        @type classname: C{string}
        @param filename: The filename from which this was instanciated
        @type filename: C{string}
        """
        gobject.GObject.__init__(self)
                
        self.name = name
        self.description = description        
        self.module_type = module_type
        self.category = category
        self.in_type = in_type
        self.out_type = out_type
        self.module = module
        
        self.classname = classname
        self.filename = filename
        self._uid = ""
        #Generate a unique identifier for this instance
        for i in range(1,ModuleWrapper.NUM_UID_DIGITS):
            self._uid += str(random.randint(0,10))
        
    def get_unique_identifier(self):
        """
        Returs a unique identifier for the module.
        
        @returns: A unuque string in the form name-somerandomdigits
        @rtype: C{string}
        """
        return "%s-%s" % (self.name, self._uid)
            
    def get_icon(self):
        """
        Gets the icon for the contained module. A bit hackish because I could
        not work out how to derive the dynamically loaded modules from this
        type. 
        
        If the contained module is not a source or a sink then
        return None for the icon
        
        @returns: An icon or None
        @rtype C{gtk.gdk.Pixbuf}
        """
        if self.module is not None:
            if isinstance(self.module, conduit.DataProvider.DataProviderBase):
                return self.module.get_icon()
        
        return None
