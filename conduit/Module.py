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
from os.path import abspath, expanduser, join, basename

import logging
import conduit, conduit.dataproviders
from conduit.ModuleWrapper import ModuleWrapper
from conduit.DataProvider import DataProviderBase
from conduit.Network import ConduitNetworkManager
from conduit.Hal import HalMonitor
from conduit.dataproviders import RemovableDeviceManager

class ModuleManager(gobject.GObject):
    """
    Generic dynamic module loader for conduit. Given a path
    it loads all modules in that directory, keeping them in an
    internam array which may be returned via get_modules

    Also manages modules like the ipod which are added and removed at
    runtime
    """
    __gsignals__ = {
        # Fired when the passed module context is loaded, that is the module's __init__ method has been called
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT]),
        "dataprovider-removed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT]),
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

        self.filelist = self._build_filelist_from_directories (dirs)
        #Modules loaded from files in the dataprovider dir
        self.fileModules = []
        #Modules that are added at runtime from ipods
        self.dynamicModules = []

        #Advertise conduit on the network
        if conduit.settings.get("enable_network") == True:
            try:
                self.networkManager = ConduitNetworkManager()
                self.networkManager.connect("dataprovider-added", self._on_dynamic_dataprovider_added)
            except:
                logging.warn("unable to initiate network, disabling..")
                # conduit.settings.set("enable_network", False)
                self.networkManager = None
 
        #Support removable devices, ipods, etc
        if conduit.settings.get("enable_removable_devices") == True:
            hal = HalMonitor()
            self.removableDeviceManager = RemovableDeviceManager(hal)
            self.removableDeviceManager.connect("dataprovider-added", self._on_dynamic_dataprovider_added)

    def _on_dynamic_dataprovider_added(self, monitor, dpw):
        #Store the ipod so it can be retrieved later by the treeview/model
        #emit a signal so it is added to the GUI
        
        logging.debug("Dynamic dataprovider (%s) added by %s" % (dpw, monitor))
        #FIXME: Should I be checking if its already in there. They cant be
        #singleton objects incase the person has multiple ipods or USB keys.
        #Hmmmmmm
        self.dynamicModules.append(dpw)
        self._emit_added(dpw)

    def _emit_added(self, dataproviderWrapper):
        if dataproviderWrapper.module_type == "source":
            self.emit("dataprovider-added", dataproviderWrapper)
        elif dataproviderWrapper.module_type == "sink":
            self.emit("dataprovider-added", dataproviderWrapper)
        else:
            #Dont emit a signal when a datatype of converter is loaded as I dont
            #think signal emission is useful in that case
            pass

    def _build_filelist_from_directories(self, directories=None):
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
        return res			
       
    def _is_module(self, filename):
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
        
    def _append_module(self, module):
        """
        Checks if the given module (checks by classname) is already loaded
        into the modulelist array, if not it is added to that array
        
        @param module: The module to append.
        @type module: L{conduit.ModuleManager.ModuleWrapper}
        """
        if module.classname not in [i.classname for i in self.fileModules]:
            self.fileModules.append(module)
        else:
            logging.warn("Module named %s allready loaded" % (module.classname))
            
    def _import_file(self, filename):
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
        
    def _load_modules_in_file(self, filename):
        """
        Loads all modules in the given file
        """
        mod = self._import_file(filename)
        if mod is None:
        	return

        for modules, infos in mod.MODULES.items():
            try:
                mod_instance = getattr (mod, modules) ()
                #Initialize the module (only DataProviders have initialize() methods
                enabled = True
                if isinstance(mod_instance,DataProviderBase):
                    if not mod_instance.initialize():
                        logging.debug("%s Starting disabled" % infos["name"])
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
                self._append_module(mod_wrapper)
                #Emit a signal to say the module was successfully loaded
                self._emit_added(mod_wrapper)
            except AttributeError:
                logging.error("Could not find module %s in %s\n%s" % (modules,filename,traceback.format_exc()))
            
    def load_static_modules(self):
        """
        Loads all modules stored in the current directory
        """
        for f in self.filelist:
            self._load_modules_in_file (f)
            
        self.emit('all-modules-loaded')
        
    def get_all_modules(self):
        """
        @returns: All loaded modules
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        """
        return self.fileModules
        
    def get_modules_by_type(self, type_filter):
        """
        Returns all loaded modules of type specified by type_filter 
        or all if the filter is set to None.
        
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        @returns: A list of L{conduit.ModuleManager.ModuleWrapper}
        """
        if type_filter is None:
            return self.fileModules
        else:
            mods = []
            for i in self.fileModules:
                if i.module_type == type_filter:
                    mods.append(i)
            
            return mods
            
    def get_new_module_instance(self, classname):
        """
        Returns a new instance ModuleWrapper specified by name
        
        @param classname: Classname of the module to get
        @type classname: C{string}
        @returns: An newly instanciated ModuleWrapper
        @rtype: a L{conduit.Module.ModuleWrapper}
        """    
        if classname in [i.classname for i in self.dynamicModules]:
            #FIXME: Shoud reinstanciate this or something.....
            #HACKHACKHACK
            for mod in self.dynamicModules:    
                if mod.classname == classname:
                    return mod
        #check if its loaded from a file (i.e. been checked and is instanciatable)
        elif classname in [i.classname for i in self.fileModules]:
            for m in self.fileModules:
                if classname == m.classname:
                    #reimport the file that the module was in
                    mods = self._import_file(m.filename)
                    #re-instanciate it
                    mod_instance = getattr (mods, m.classname) ()
                    #Initialize the module (only DataProviders have initialize() methods
                    enabled = True
                    if isinstance(mod_instance,DataProviderBase):
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
        else:
            logging.warn("Could not find module with class name %s" % (classname))        
            return None
            
