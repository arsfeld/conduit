import gtk
import gobject
import random

import logging
import conduit

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
    @ivar initargs: The arguments the module was initialised with
    @type initargs: C{tuple}
    @ivar module: The name of the contained module
    @type module: L{conduit.DataProvider.DataProvider} or derived class     
    @ivar enabled: Whether the call to the modules initialize() method was
    successful or not. 
    @type enabled: C{bool}    
    @ivar uid: A Unique identifier for the module
    @type uid: C{string}
    @ivar icon: An icon representing this wrapper or the module it holds
    @type icon: C{pixbuf}
    """
    
    NUM_UID_DIGITS = 5
    COMPULSORY_ATTRIBUTES = [
                            "name",
                            "description",
                            "icon",
                            "type",
                            "category",
                            "in_type",
                            "out_type"
                            ]
    	
    def __init__ (self, name, description, icon, module_type, category, in_type, out_type, classname, initargs, module=None, enabled=True):
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
        @param filename: The arguments the module was initialised with
        @type filename: C{tuple}
        @param module: The name of the contained module
        @type module: L{conduit.DataProvider.DataProvider} or derived class     
        @param enabled: Whether the call to the modules initialize() method was
        successful or not. 
        @type enabled: C{bool}
        """
        self.name = name
        self.description = description 
        self.icon_name = icon       
        self.module_type = module_type
        self.category = category
        self.in_type = in_type
        self.out_type = out_type
        self.classname = classname
        #Initargs must be a tuple or a list for get_key() to work
        if type(initargs) == tuple:
            self.initargs = initargs
        else:
            logging.warn("BAD PROGRAMMER ---- INIT ARGS MUST BE A TUPLE (was a %s)" % type(initargs))
            self.initargs = ()
        self.module = module
        self.enabled = enabled
        
        self._uid = ""
        #Generate a unique identifier for this instance
        for i in range(1,ModuleWrapper.NUM_UID_DIGITS):
            self._uid += str(random.randint(0,10))

        self.icon_path = ""
        self.icon = None

    def get_key(self):
        """
        Returns a string in the form of classname:initarg0:initarg1:...
    
        I suppose I could have used the builtin __getinitargs__ call used with 
        pickle but requires less implementation detail on the part of the DP
        """
        return self.classname + ":" + ":".join(self.initargs)
       
    def get_unique_identifier(self):
        """
        Returs a unique identifier for the module.
        
        @returns: A unuque string in the form name-somerandomdigits
        @rtype: C{string}
        """
        return "%s-%s" % (self.get_key(), self._uid)

    def get_icon(self):
        """
        Returns the icon for the module contained in this wrapper.
        In the case of a sink or source this is easy as the module
        contains the icon.

        Wrappers derived from this class (such as the CategoryWrapper)
        should override this function
        """
        if self.module_type == "source" or self.module_type == "sink" or self.module_type == "category":
            if self.icon is None:
                try:
                    info = gtk.icon_theme_get_default().lookup_icon(self.icon_name, 16, 0)
                    self.icon = info.load_icon()
                    self.icon_path = info.get_filename()
                except gobject.GError:
                    self.icon = None
                    logging.error("Could not load icon %s" % self.icon_name)
                    #Last resort: Try the non icon-naming-spec compliant icon
                    self.icon_name = "gtk-missing-image"
                    info = gtk.icon_theme_get_default().lookup_icon(self.icon_name, 16, 0)
                    self.icon = info.load_icon()
                    self.icon_path = info.get_filename()

        return self.icon
        
    def __str__(self):
        return "%s %s wrapper (UID: %s)" % (self.name, self.module_type, self.get_unique_identifier())
