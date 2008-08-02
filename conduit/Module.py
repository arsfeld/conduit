"""
Classes associated with dynamic module loading

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject
import os, os.path
import traceback
import pydoc
import logging
log = logging.getLogger("Module")

import conduit.dataproviders
import conduit.ModuleWrapper as ModuleWrapper
import conduit.Knowledge as Knowledge
import conduit.Vfs as Vfs

class ModuleManager(gobject.GObject):
    """
    Generic dynamic module loader for conduit. Given a path
    it loads all modules in that directory, keeping them in an
    internam array which may be returned via get_modules

    Also manages dataprovider factories which make dataproviders available
    at runtime
    """
    __gsignals__ = {
        #Fired when a new instantiatable DP becomes available. It is described via 
        #a wrapper because we do not actually instantiate it till later - to save memory
        "dataprovider-available" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    #The DPW describing the new DP class
        "dataprovider-unavailable" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    #The DPW describing the DP class which is now unavailable
        # Fired when load_all has loaded every available modules
        "all-modules-loaded" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        # Fired when a syncset is created
        "syncset-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    #The syncset that was added
        }
       
    def __init__(self, dirs=None):
        """
        @param dirs: A list of directories to search. Relative pathnames and paths
        containing ~ will be expanded. If dirs is None the 
        ModuleLoader will not search for modules.
        @type dirs: C{string[]}
        """
        gobject.GObject.__init__(self)
        #Dict of loaded modulewrappers. key is wrapper.get_key()
        #Stored seperate to the classes because dynamic dataproviders may
        #use the same class but with different initargs (diff keys)
        self.moduleWrappers = {}
        #Files that could not be loaded properly
        self.invalidFiles = []
        #Keep a ref to dataprovider factories so they are not collected
        self.dataproviderFactories = []
        #scan all dirs for files in the right format (*Module/*Module.py)
        self.filelist = self._build_filelist_from_directories(dirs)

    def _on_dynamic_dataprovider_added(self, monitor, dpw, klass):
        """
        Store the ipod so it can be retrieved later by the treeview/model
        emit a signal so it is added to the GUI
        """
        log.info("Dynamic dataprovider (%s) available by %s" % (dpw, monitor))
        self._append_module(dpw, klass)

    def _on_dynamic_dataprovider_removed(self, monitor, key):
        log.info("Dynamic dataprovider (%s) unavailable by %s" % (key, monitor))
        self._remove_module(key)

    def _emit_available(self, dataproviderWrapper):
        if dataproviderWrapper.module_type in ["source", "sink", "twoway"]:
            self.emit("dataprovider-available", dataproviderWrapper)

    def _emit_unavailable(self, dataproviderWrapper):
        if dataproviderWrapper.module_type in ["source", "sink", "twoway"]:
            self.emit("dataprovider-unavailable", dataproviderWrapper)

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
                log.warn("Error reading directory %s, skipping." % (d))
        return res            
       
    def _is_module(self, filename):
        return filename.endswith("Module.py")

    def _is_module_dir(self, dirname):
        return dirname.endswith("Module")
        
    def _append_module(self, wrapper, klass):
        #Check if the wrapper is unique
        key = wrapper.get_dnd_key()
        if key not in self.moduleWrappers:
            self.moduleWrappers[key] = wrapper
            #Emit a signal because this wrapper is new
            self._emit_available(wrapper)
        else:
            log.warn("Wrapper with key %s allready loaded" % key)
    
    def _remove_module(self, key):
        """
        Looks for a given key in the class registry and attempts to remove it
        
        @param key: The key of the class to remove
        """
        
        if not key in self.moduleWrappers:
            log.warn("Unable to remove class - it isn't available! (%s)" % key)
            return

        #keep a ref for the signal emission
        dpw = self.moduleWrappers[key]

        # remove from moduleWrappers...
        del self.moduleWrappers[key]
        # notify everything that dp is no longer available
        self._emit_unavailable(dpw)

    def _import_file(self, filename):
        """
        Tries to import the specified file. Returns the python module on succes.
        Primarily for internal use. Note that the python module returned may actually
        contain several more loadable modules.
        """
        mods = pydoc.importfile (filename)
        try:
            if (mods.MODULES): pass
        except AttributeError:
            log.warn("The file %s is not a valid module. Skipping." % (filename))
            log.warn("A module must have the variable MODULES defined as a dictionary.")
            raise
        for modules, infos in mods.MODULES.items():
            for i in ModuleWrapper.COMPULSORY_ATTRIBUTES:
                if i not in infos:
                    log.warn("Class %s in file %s does define a %s attribute. Skipping." % (modules, filename, i))
                    raise Exception
        return mods

    def _load_modules_in_file(self, filename):
        """
        Loads all modules in the given file
        """
        try:
            mod = self._import_file(filename)
            for modules, infos in mod.MODULES.items():
                try:
                    klass = getattr(mod, modules)
                    if infos["type"] == "dataprovider" or infos["type"] == "converter":
                        mod_wrapper = ModuleWrapper.ModuleWrapper(
                                        klass=klass,
                                        initargs=(),
                                        category=getattr(klass, "_category_", conduit.dataproviders.CATEGORY_TEST)
                                        )
                        #Save the module (signal is emitted in _append_module)
                        self._append_module(
                                mod_wrapper,
                                klass
                                )
                    elif infos["type"] == "dataprovider-factory":
                        # build a dict of kwargs to pass to factories
                        kwargs = {
                            "moduleManager": self,
                        }
                        #instantiate and store the factory
                        instance = klass(**kwargs)
                        self.dataproviderFactories.append(instance)
                    else:
                        log.warn("Class is an unknown type: %s" % klass)
                except AttributeError:
                    log.warn("Could not find module %s in %s\n%s" % (modules,filename,traceback.format_exc()))
        except Exception, e:
            log.warn("Error loading the file: %s\n%s" % (filename, traceback.format_exc()))
            self.invalidFiles.append(os.path.basename(filename))

    def load_all(self, whitelist, blacklist):
        """
        Loads all classes in the configured paths.

        If whitelist and blacklist are supplied then the name of the file
        is tested against them. Default policy is to load all modules unless
        """
        for f in self.filelist:
            name, ext = Vfs.uri_get_filename_and_extension(f)
            if whitelist:
                if name in whitelist:
                    self._load_modules_in_file(f)
            elif blacklist:
                if name not in blacklist: 
                    self._load_modules_in_file(f)
            else:            
                self._load_modules_in_file(f)

        for i in self.dataproviderFactories:
            i.connect("dataprovider-removed", self._on_dynamic_dataprovider_removed)
            i.connect("dataprovider-added", self._on_dynamic_dataprovider_added)
            i.probe()

        self.emit('all-modules-loaded')
            
    def get_all_modules(self):
        """
        @returns: All loaded modules
        @rtype: L{conduit.ModuleManager.ModuleWrapper}[]
        """
        return self.moduleWrappers.values()
        
    def get_modules_by_type(self, *type_filter):
        """
        Returns all loaded modules of type specified by type_filter 
        or all if the filter is set to None.
        """
        if len(type_filter) == 0:
            return self.moduleWrappers.values()
        return [i for i in self.moduleWrappers.values() if i.module_type in type_filter]
            
    def get_module_wrapper_with_instance(self, wrapperKey):
        """
        Returns a new ModuleWrapper with a dp instace described by wrapperKey
        """
        mod_wrapper = None
    
        if wrapperKey in self.moduleWrappers:
            #Get the existing wrapper
            m = self.moduleWrappers[wrapperKey]
            #Make a copy of it, containing an instantiated module
            mod_wrapper = ModuleWrapper.ModuleWrapper(
                            klass=m.klass,
                            initargs=m.initargs,
                            category=m.category
                            )
            mod_wrapper.instantiate_module()
        else:
            log.warn("Could not find module wrapper: %s" % (wrapperKey))
            mod_wrapper = ModuleWrapper.PendingDataproviderWrapper(wrapperKey)

        return mod_wrapper

    def make_modules_callable(self, type_filter):
        """
        If it is necesary to call the modules directly. This
        function creates those instances in wrappers of the specified type
        """
        for i in self.moduleWrappers.values():
            if i.module_type == type_filter:
                i.instantiate_module()
                
    def list_preconfigured_conduits(self):
        #strip the keys back to the classnames, because the preconfigured dps
        #are described in terms of classes, not instances (keys)
        names = {}
        for key in self.moduleWrappers:
            names[key.split(":")[0]] = key
            
        #for a preconfigured conduit to be available, both the 
        #source and sink must be loaded
        found = []
        for (source,sink),(comment,twoway) in Knowledge.PRECONFIGIRED_CONDUITS.items():
            if source in names and sink in names:
                #return key,key,desc,two-way
                found.append( (names[source],names[sink],comment,twoway) )

        return found

    def quit(self):
        for dpf in self.dataproviderFactories:
            dpf.quit()





