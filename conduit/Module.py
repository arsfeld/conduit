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
        #Fired when a new instantiatable DP becomes available. It is described via 
        #a wrapper because we do not actually instantiate it till later - to save memory
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    #The DPW describing the new DP class
        "dataprovider-removed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    #The DPW describing the DP class which is now unavailable
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

        #Dict of loaded classes, key is classname, value is class
        self.classRegistry = {}
        #Dict of loaded modulewrappers. key is wrapper.get_key()
        #Stored seperate to the classes because removable devices may
        #use the same class but with different initargs (diff keys)
        self.moduleWrappers = {}

        #FIXME: Disable per the classregistry rewrite working ok with removable devices
        #Advertise conduit on the network
        #if conduit.settings.get("enable_network") == True:
        #    try:
        #        self.networkManager = ConduitNetworkManager()
        #        self.networkManager.connect("dataprovider-added", self._on_dynamic_dataprovider_added)
        #    except:
        #        logging.warn("Unable to initiate network, disabling..")
        #        # conduit.settings.set("enable_network", False)
        #        self.networkManager = None
 
        #Support removable devices, ipods, etc
        if conduit.settings.get("enable_removable_devices") == True:
            hal = HalMonitor()
            self.removableDeviceManager = RemovableDeviceManager(hal)
            self.removableDeviceManager.connect("dataprovider-added", self._on_dynamic_dataprovider_added)

    def _on_dynamic_dataprovider_added(self, monitor, dpw, klass):
        """
        Store the ipod so it can be retrieved later by the treeview/model
        emit a signal so it is added to the GUI
        """
        logging.info("Dynamic dataprovider (%s) added by %s" % (dpw, monitor))
        self._append_module(dpw, klass)

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
        
    def _append_module(self, wrapper, klass):
        """
        Checks if the given module (checks by classname) is already loaded
        into the modulelist array, if not it is added to that array
        
        @param module: The module to append.
        @type module: L{conduit.ModuleManager.ModuleWrapper}
        """
        #Check if the class is unique
        classname = klass.__name__
        if classname not in self.classRegistry:
            self.classRegistry[classname] = klass
        else:
            logging.warn("Class named %s allready loaded" % (classname))
        #Check if the wrapper is unique
        key = wrapper.get_key()
        if key not in self.moduleWrappers:
            self.moduleWrappers[key] = wrapper
            #Emit a signal because this wrapper is new
            self._emit_added(wrapper)
        else:
            logging.info("Wrapper with key %s allready loaded" % key)
            
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
                klass = getattr(mod, modules)
                mod_wrapper = ModuleWrapper (   infos["name"], 
            	                                infos["description"], 
                                                infos["icon"],
            	                                infos["type"], 
            	                                infos["category"], 
            	                                infos["in_type"],
            	                                infos["out_type"],
            	                                klass.__name__,     #classname
            	                                (),                 #Init args
            	                                )
                #Save the module (signal is emitted _append_module
                self._append_module(mod_wrapper, klass)
            except AttributeError:
                logging.error("Could not find module %s in %s\n%s" % (modules,filename,traceback.format_exc()))

    def _instantiate_class(self, classname, initargs):
        if type(initargs) != tuple:
            logging.warn("Could not make class %s. Initargs must be a tuple" % classname)
            return None
        if classname in self.classRegistry:
            logging.info("Returning new instance: Classname=%s Initargs=%s" % (classname,initargs))
            #FIXME: HACK HACK HACK. Saves me having to implement __new__ in 
            #base dataprovider. I can back this out when I have full pyro support
            #for remote networked conduit instances
            #http://www.python.org/download/releases/2.2.3/descrintro/#__new__
            if len(initargs) == 0:
                return self.classRegistry[classname]()
            if len(initargs) == 1:
                return self.classRegistry[classname](initargs[0])
            elif len(initargs) == 2:
                return self.classRegistry[classname](initargs[0],initargs[1])
            elif len(initargs) == 3:
                return self.classRegistry[classname](initargs[0],initargs[1],initargs[2])
            else:
                logging.critical("BAD PROGRAMMER. NUMBER OF INIT ARGS EXCEEDS HACKISH WORKAROUND")
        else:
            logging.warn("Could not find class named %s" % classname)

            
    def load_static_modules(self):
        """
        Loads all modules. Slow blocking call to be used at startup
        Necessary because settings cannot be restored until all modules
        are loaded, and hence we cant wait for signals
        """
        for f in self.filelist:
            self._load_modules_in_file (f)

        #if self.networkManager:
        #    #self.networkManager.load_all_modules()
        #    #self.dynamicModules += self.networkManager.get_all_modules()
             
        if conduit.settings.get("enable_removable_devices") == True:
            mods = self.removableDeviceManager.get_all_modules()
            for wrapper, klass in mods:
                self._append_module(wrapper, klass)
            
        self.emit('all-modules-loaded')
        
    def get_all_modules(self):
        """
        @returns: All loaded modules
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        """
        return self.moduleWrappers.values()
        
    def get_modules_by_type(self, type_filter):
        """
        Returns all loaded modules of type specified by type_filter 
        or all if the filter is set to None.
        
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        @returns: A list of L{conduit.ModuleManager.ModuleWrapper}
        """
        if type_filter is None:
            return self.moduleWrappers.values()
        else:
            #sorry about the one-liner
            return [i for i in self.moduleWrappers.values() if i.module_type == type_filter]
            
    def get_new_module_instance(self, wrapperKey):
        """
        Returns a new instance ModuleWrapper specified by name
        
        @param classname: Classname of the module to get
        @type classname: C{string}
        @returns: An newly instanciated ModuleWrapper
        @rtype: a L{conduit.Module.ModuleWrapper}
        """    
        if wrapperKey in self.moduleWrappers:
            #Get the existing wrapper
            m = self.moduleWrappers[wrapperKey]
            #Get its construction args
            classname = m.classname
            initargs = m.initargs
            mod_wrapper = ModuleWrapper(  
                                        m.name, 
    	                                m.description,
                                        m.icon_name, 
    	                                m.module_type, 
    	                                m.category, 
    	                                m.in_type,
    	                                m.out_type,
    	                                classname,
    	                                initargs,
    	                                self._instantiate_class(classname, initargs),
    	                                True)
                
            return mod_wrapper
        else:
            logging.warn("Could not find module wrapper: %s" % (wrapperKey))
            print self.moduleWrappers.keys()
            return None

    def make_modules_callable(self, type_filter):
        """
        In the typeconverter it is necesary to call the modules directly. This
        function creates those instances in wrappers of the specified type
        """
        for i in self.moduleWrappers.values():
            if i.module_type == type_filter:
                i.module = self._instantiate_class(i.classname, i.initargs)

