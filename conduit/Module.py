"""
Classes associated with dynamic module loading

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject
import os, os.path
import traceback
import pydoc

from conduit import log,logd,logw
from conduit.ModuleWrapper import ModuleWrapper
from conduit.DataProvider import CATEGORY_TEST
from conduit.Hal import HalMonitor

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
        self.hal = HalMonitor()

        #Dict of loaded classes, key is classname, value is class
        self.classRegistry = {}
        #Dict of loaded modulewrappers. key is wrapper.get_key()
        #Stored seperate to the classes because dynamic dataproviders may
        #use the same class but with different initargs (diff keys)
        self.moduleWrappers = {}
        #Keep a ref to dataprovider factories so they are not collected
        self.dataproviderFactories = []

        #Now load all directories containing MODULES
        #(includes dataproviders, converters and dynamic-dataproviders)
        filelist = self._build_filelist_from_directories(dirs)
        for f in filelist:
            self._load_modules_in_file(f)

        for i in self.dataproviderFactories:
            i.connect("dataprovider-removed", self._on_dynamic_dataprovider_removed)
            i.connect("dataprovider-added", self._on_dynamic_dataprovider_added)
            i.probe()

        self.emit('all-modules-loaded')

    def _on_dynamic_dataprovider_added(self, monitor, dpw, klass):
        """
        Store the ipod so it can be retrieved later by the treeview/model
        emit a signal so it is added to the GUI
        """
        log("Dynamic dataprovider (%s) added by %s" % (dpw, monitor))
        self._append_module(dpw, klass)

    def _on_dynamic_dataprovider_removed(self, monitor, key):
        log("Dynamic dataprovider (%s) removed by %s" % (key, monitor))
        self._remove_module(key)

    def _emit_added(self, dataproviderWrapper):
        if dataproviderWrapper.module_type in ["source", "sink", "twoway"]:
            self.emit("dataprovider-added", dataproviderWrapper)
        else:
            #Dont emit a signal when a datatype of converter is loaded as I dont
            #think signal emission is useful in that case
            pass

    def _emit_removed(self, dataproviderWrapper):
        if dataproviderWrapper.module_type in ["source", "sink", "twoway"]:
            self.emit("dataprovider-removed", dataproviderWrapper)

    def _build_filelist_from_directories(self, directories=None):
        """
        Converts a given array of directories into a list 
        containing the filenames of all qualified modules. Recurses into
        directories and adds files if they have the same name as the
        directory in which they reside.
        This method is automatically invoked by the constructor.
        """
        res = []
        if not directories:
            return res
            
        #convert to abs path    
        directories = [os.path.abspath(os.path.expanduser(s)) for s in directories]

        while len(directories) > 0:
            d = directories.pop(0)
            log("Reading directory %s" % d)
            try:
                if not os.path.exists(d):
                    continue
                for i in os.listdir(d):
                    f = os.path.join(d,i)
                    if os.path.isfile(f) and self._is_module(f):
                        if os.path.basename(f) not in [os.path.basename(j) for j in res]:
                            res.append(f)
                    elif os.path.isdir(f) and self._is_module_dir(f):
                        directories.append(f)
            except OSError, err:
                logw("Error reading directory %s, skipping." % (d))
        return res            
       
    def _is_module(self, filename):
        """
        Tests whether the filename has the appropriate extension.
        """
        endswith = "Module.py"
        isModule = filename[-len(endswith):] == endswith
        return isModule

    def _is_module_dir(self, dirname):
        endswith = "Module"
        isModuleDir = dirname[-len(endswith):] == endswith
        return isModuleDir
        
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
            logw("Class named %s allready loaded" % (classname))
        #Check if the wrapper is unique
        key = wrapper.get_key()
        if key not in self.moduleWrappers:
            self.moduleWrappers[key] = wrapper
            #Emit a signal because this wrapper is new
            self._emit_added(wrapper)
        else:
            log("Wrapper with key %s allready loaded" % key)
    
    def _remove_module(self, key):
        """
        Looks for a given key in the class registry and attempts to remove it
        
        @param key: The key of the class to remove
        """
        
        if not key in self.moduleWrappers:
            logw("Unable to remove class - it isn't available! (%s)" % key)
            return

        # notify everything that dp is no longer available
        self._emit_removed(self.moduleWrappers[key])

        # remove from moduleWrappers...
        del self.moduleWrappers[key]

    def _import_file(self, filename):
        """
        Tries to import the specified file. Returns the python module on succes.
        Primarily for internal use. Note that the python module returned may actually
        contain several more loadable modules.
        """
        try:
            mods = pydoc.importfile (filename)
        except Exception:
            logw("Error loading the file: %s.\n%s" % (filename, traceback.format_exc()))
            return

        try:
            if (mods.MODULES): pass
        except AttributeError:
            logw("The file %s is not a valid module. Skipping." % (filename))
            logw("A module must have the variable MODULES defined as a dictionary.")
            return

        for modules, infos in mods.MODULES.items():
            for i in ModuleWrapper.COMPULSORY_ATTRIBUTES:
                if i not in infos:
                    logw("Class %s in file %s does define a %s attribute. Skipping." % (modules, filename, i))
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

                if infos["type"] == "dataprovider" or infos["type"] == "converter":
                    mod_wrapper = ModuleWrapper (   
                                        getattr(klass, "_name_", ""),
                                        getattr(klass, "_description_", ""),
                                        getattr(klass, "_icon_", ""),
                                        getattr(klass, "_module_type_", infos["type"]),
                                        getattr(klass, "_category_", CATEGORY_TEST),
                                        getattr(klass, "_in_type_", ""),
                                        getattr(klass, "_out_type_", ""),
                                        klass.__name__,     #classname
                                        (),                 #Init args
                                        )
                    #Save the module (signal is emitted _append_module
                    self._append_module(mod_wrapper, klass)
                elif infos["type"] == "dataprovider-factory":
                    # build a dict of kwargs to pass to factories
                    kwargs = {
                        "hal":    self.hal,
                        "moduleManager": self,
                    }
                    #instantiate and store the factory
                    instance = klass(**kwargs)
                    self.dataproviderFactories.append(instance)
                else:
                    logw("Class %s is an unknown type: %s" % (klass.__name__, infos["type"]))
            except AttributeError:
                logw("Could not find module %s in %s\n%s" % (modules,filename,traceback.format_exc()))

    def _instantiate_class(self, classname, initargs):
        if type(initargs) != tuple:
            logw("Could not make class %s. Initargs must be a tuple" % classname)
            return None
        if classname in self.classRegistry:
            log("Returning new instance: Classname=%s Initargs=%s" % (classname,initargs))
            return self.classRegistry[classname](*initargs)
        else:
            logw("Could not find class named %s" % classname)

            
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
            logw("Could not find module wrapper: %s" % (wrapperKey))
            return None

    def make_modules_callable(self, type_filter):
        """
        If it is necesary to call the modules directly. This
        function creates those instances in wrappers of the specified type
        """
        for i in self.moduleWrappers.values():
            if i.module_type == type_filter:
                i.module = self._instantiate_class(i.classname, i.initargs)

class DataProviderFactory(gobject.GObject):
    """
    Abstract base class for a factory which emits Dataproviders. Users should 
    inherit from this if they wish to provide a loadable module in which
    dynamic dataproviders are added and removed at runtime.
    """
    __gsignals__ = {
        #Fired when the module detects a usb key or ipod added
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT,      #Wrapper
            gobject.TYPE_PYOBJECT]),    #Class
        "dataprovider-removed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING])     #Unique key
    }

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

    def emit_added(self, klass, initargs=(), category=None):
        if category == None:
            category = getattr(klass, "_category_", CATEGORY_TEST)
        dpw = ModuleWrapper (   
                    getattr(klass, "_name_", ""),
                    getattr(klass, "_description_", ""),
                    getattr(klass, "_icon_", ""),
                    getattr(klass, "_module_type_", ""),
                    category,
                    getattr(klass, "_in_type_", ""),
                    getattr(klass, "_out_type_", ""),
                    klass.__name__,     #classname
                    initargs,
                    )
        log("DataProviderFactory %s: Emitting dataprovider-added for %s" % (self, dpw.get_key()))
        self.emit("dataprovider-added", dpw, klass)
        return dpw.get_key()

    def emit_removed(self, key):
        log("DataProviderFactory.emit_removed(): For %s" % key)
        self.emit("dataprovider-removed", key)

    def probe(self):
        pass


