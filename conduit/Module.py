"""
Classes associated with dynamic module loading

Copyright: John Stowers, 2006
License: GPLv2
"""

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


class ModuleLoader(gobject.GObject):
    """
    Generic dynamic module loader for conduit. Given a path
    it loads all modules in that directory, keeping them in an
    internam array which may be returned via get_modules
    """
    __gsignals__ = {
        # Fired when the passed module context is loaded, that is the module's __init__ method has been called
        "module-loaded" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT]),
        # Fired when load_all has loaded every available modules
        "all-modules-loaded" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
        }
       
    def __init__(self, dirs=None):
        """
		@param dirs: A list of directories to search. Relative pathnames and paths
		containing ~ will be expanded. If dirs is None the 
		ModuleLoader will not search for modules.
		@type dirs: C{string[]}
		"""
        gobject.GObject.__init__(self)

        self.loadedmodules = []
        self.filelist = self.build_filelist_from_directories (dirs)
           
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
        return res			
       
    def is_module(self, filename):
        """
        Tests whether the filename has the appropriate extension.
        """
        endswith = "Module.py"
        isModule = (filename[-len(endswith):] == endswith)
        if not isModule:
            logging.debug(  "Ignoring %s, (must end with %s)" % (
                            filename,
                            endswith
                            ))
        return isModule
        
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
            logging.error("Error loading the file: %s.\n%s" % (filename, traceback.format_exc()))
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
            try:
                mod_instance = getattr (mod, modules) ()
                #Initialize the module (only DataProviders have initialize() methods
                enabled = True
                if isinstance(mod_instance,DataProvider.DataProviderBase):
                    if not mod_instance.initialize():
                        logging.warn("%s did not initialize correctly. Starting disabled" % infos["name"])
                        enabled = False
                
                mod_wrapper = ModuleWrapper (  infos["name"], 
            	                               infos["description"], 
            	                               infos["type"], 
            	                               infos["category"], 
            	                               infos["in_type"],
            	                               infos["out_type"],
            	                               str(modules),    #classname
            	                               filename,        #file holding me
            	                               mod_instance,    #the actual module
            	                               enabled)         #did initialize() return correctly
                self.append_module(mod_wrapper)
                #Emit a signal to say the module was successfully loaded
                self.emit("module-loaded", mod_wrapper)
            except AttributeError:
                logging.error("Could not find module %s in %s\n%s" % (modules,filename,traceback.format_exc()))
            
    def load_all_modules(self):
        """
        Loads all modules stored in the current directory
        """
        for f in self.filelist:
            self.load_modules_in_file (f)
            
        self.emit('all-modules-loaded')
        
    def get_all_modules(self):
        """
        @returns: All loaded modules
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        """
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
            
    def get_module_named(self, classname):
        """
        Returns a ModuleWrapper specified by name
        
        @param classname: Classname of the module to get
        @type classname: C{string}
        @returns: An already instanciated ModuleWrapper
        @rtype: a L{conduit.Module.ModuleWrapper}
        """
        for m in self.loadedmodules:
            if classname == m.classname:
                logging.info("Returning module named %s" % (classname))
                return m
                
        logging.warn("Could not find module with classname %s" % (classname))
        return None
                
    def get_new_instance_module_named(self, classname):
        """
        Returns a new instance ModuleWrapper specified by name
        
        @param classname: Classname of the module to get
        @type classname: C{string}
        @returns: An newly instanciated ModuleWrapper
        @rtype: a L{conduit.Module.ModuleWrapper}
        """    
        #check if its loaded (i.e. been checked and is instanciatable)
        if classname in [i.classname for i in self.loadedmodules]:
            for m in self.loadedmodules:
                if classname == m.classname:
                    #reimport the file that the module was in
                    mods = self.import_file(m.filename)
                    #re-instanciate it
                    mod_instance = getattr (mods, m.classname) ()
                    #Initialize the module (only DataProviders have initialize() methods
                    enabled = True
                    if isinstance(mod_instance,DataProvider.DataProviderBase):
                        if not mod_instance.initialize():
                            logging.warn("%s did not initialize correctly. Starting disabled" % m.classname)
                            enabled = False                  
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
            	                               mod_instance,
            	                               enabled)
                    
                    logging.info("Returning new instance of module with classname %s" % (m.classname))
                    return mod_wrapper
        #Didnt load at app startup so its not gunna load now!
        logging.warn("Could not find module with class name %s" % (classname))        
        return None
            
class ModuleWrapper: 
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
    @ivar in_type: The name of the datatype that the module accepts (put())
    @type in_type: C{string}
    @ivar out_type: The name of the datatype that the module produces (get())
    @type out_type: C{string}        
    @ivar classname: The classname used to instanciate another
    modulewrapper of type C{module} contained in C{filename}
    @type classname: C{string}
    @ivar filename: The filename from which this was instanciated
    @type filename: C{string}
    @ivar module: The name of the contained module
    @type module: L{conduit.DataProvider.DataProvider} or derived class     
    @ivar enabled: Whether the call to the modules initialize() method was
    successful or not. 
    @type enabled: C{bool}    
    @ivar uid: A Unique identifier for the module
    @type uid: C{string}
    @ivar icon: A Unique identifier for the module
    @type icon: C{pixbuf}
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
    	
    def __init__ (self, name, description, module_type, category, in_type, out_type, classname, filename, module, enabled):
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
        @param in_type: The name of the datatype that the module accepts (put())
        @type in_type: C{string}
        @param out_type: The name of the datatype that the module produces (get())
        @type out_type: C{string}        
        @param classname: The classname used to instanciate another
        modulewrapper of type C{module} contained in C{filename}
        @type classname: C{string}
        @param filename: The filename from which this was instanciated
        @type filename: C{string}
        @param module: The name of the contained module
        @type module: L{conduit.DataProvider.DataProvider} or derived class     
        @param enabled: Whether the call to the modules initialize() method was
        successful or not. 
        @type enabled: C{bool}
        """
        self.name = name
        self.description = description        
        self.module_type = module_type
        self.category = category
        self.in_type = in_type
        self.out_type = out_type
        self.classname = classname
        self.filename = filename
        self.module = module
        self.enabled = enabled
        
        self._uid = ""
        #Generate a unique identifier for this instance
        for i in range(1,ModuleWrapper.NUM_UID_DIGITS):
            self._uid += str(random.randint(0,10))

        #Get the icon from the contained module
        self.icon = None
        if self.module != None:
            self.icon = module.get_icon()
        
    def get_unique_identifier(self):
        """
        Returs a unique identifier for the module.
        
        @returns: A unuque string in the form name-somerandomdigits
        @rtype: C{string}
        """
        return "%s-%s" % (self.classname, self._uid)
        
    def __str__(self):
        return "%s %s wrapper (UID: %s)" % (self.name, self.module_type, self.get_unique_identifier())
