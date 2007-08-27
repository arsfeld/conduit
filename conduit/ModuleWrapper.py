import gtk

from conduit import log,logd,logw
import traceback

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
    @ivar icon: An icon representing this wrapper or the module it holds
    @type icon: C{pixbuf}
    """
    
    NUM_UID_DIGITS = 5
    COMPULSORY_ATTRIBUTES = [
                            "type"
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
            logw("INIT ARGS MUST BE A TUPLE (was a %s)" % type(initargs))
            self.initargs = ()
        self.module = module
        self.enabled = enabled
        
        self.icon_path = ""
        self.icon = {}
        self.descriptiveIcon = None

    def get_key(self):
        """
        Returns a string in the form of classname:initarg0:initarg1:...
    
        I suppose I could have used the builtin __getinitargs__ call used with 
        pickle but requires less implementation detail on the part of the DP
        """
        if len(self.initargs) > 0:
            return self.classname + ":" + ":".join(self.initargs)
        else:
            return self.classname
       
    def get_UID(self):
        """
        Returs a unique identifier for the module and its contained
        dataprovider.
        @rtype: C{string}
        """
        if self.module == None:
            muid = "None"
        else:
            muid = self.module.get_UID()
        return "%s-%s" % (self.get_key(), muid)

    def get_in_type(self):
        """
        Returns the in_type for the module. If the module has not yet been 
        initialised then its in_type is derived from its class attributes. 
        If it has been initialised then it can supply its own in_type
        """
        if self.module == None:
            return self.in_type
        else:
            return self.module.get_in_type()

    def get_out_type(self):
        """
        Returns the out_type for the module. See get_in_type()
        """
        if self.module == None:
            return self.out_type
        else:
            return self.module.get_out_type()


    def get_icon(self, size=16):
        """
        Returns the icon for the module contained in this wrapper.
        In the case of a sink or source this is easy as the module
        contains the icon.

        Wrappers derived from this class (such as the CategoryWrapper)
        may override this function
        """
        if not self.icon.has_key(size) or self.icon[size] is None:
            if self.module_type in ["source", "sink", "twoway", "category"]:
                try:
                    info = gtk.icon_theme_get_default().lookup_icon(self.icon_name, size, 0)
                    self.icon[size] = info.load_icon()
                    self.icon_path = info.get_filename()
                except:
                    self.icon[size] = None
                    logw("Could not load icon %s for %s" % (self.icon_name, self.name))
                    #Last resort: Try the non icon-naming-spec compliant icon
                    self.icon_name = "gtk-missing-image"
                    info = gtk.icon_theme_get_default().lookup_icon(self.icon_name, size, 0)
                    self.icon[size] = info.load_icon()
                    self.icon_path = info.get_filename()

        return self.icon[size]

    def get_descriptive_icon(self):

        #  _____
        # |     |___
        # |  i  | a |
        # |_____|___|

        #The descriptive icon is two icons composited side by side. On the left
        #is the dataprovider icon, on the right an arrow indicating its type
        #size of each icon
        isize = 24
        asize = 16
        bwidth = isize + asize
        bheight = max(isize, asize)

        if self.descriptiveIcon is None:
            if self.module_type in ["source", "sink", "twoway"]:
                try:
                    icon = self.get_icon(isize)
                    arrowName = "conduit-"+self.module_type
                    arrow = gtk.icon_theme_get_default().load_icon(arrowName, asize, 0)

                    #Composite the arrow to the right of the icon
                    dest = gtk.gdk.Pixbuf(
                                    colorspace=gtk.gdk.COLORSPACE_RGB,
                                    has_alpha=True,
                                    bits_per_sample=8,
                                    width=bwidth,
                                    height=bheight
                                    )
                    dest.fill(0)

                    #Composite the icon on the left
                    icon.composite(
                                dest=dest,
                                dest_x=0,           #right of icon
                                dest_y=0,           #at the top
                                dest_width=isize,   #use whole arrow 1:1
                                dest_height=isize,  #ditto
                                offset_x=0,
                                offset_y=0,
                                scale_x=1,
                                scale_y=1,
                                interp_type=gtk.gdk.INTERP_NEAREST,
                                overall_alpha=255
                                )
                    #Arrow on the right
                    arrow.composite(
                                dest=dest,
                                dest_x=isize,       #right of icon
                                dest_y=isize-asize, #at the bottom
                                dest_width=asize,   #use whole arrow 1:1
                                dest_height=asize,  #ditto
                                offset_x=isize,     #move self over to the right
                                offset_y=isize-asize,#at the bottom
                                scale_x=1,
                                scale_y=1,
                                interp_type=gtk.gdk.INTERP_NEAREST,
                                overall_alpha=255
                                )
                    self.descriptiveIcon = dest
                except:
                    traceback.print_exc()
                    pass
            
            elif self.module_type == "category":
                self.descriptiveIcon = self.get_icon(isize)
    
        return self.descriptiveIcon
        
    def __str__(self):
        return "Wrapper: %s %s (UID: %s)" % (self.name, self.module_type, self.get_UID())

    def set_configuration_xml(self, xmltext):
        self.module.set_configuration_xml(xmltext)

    def get_configuration_xml(self):
        return self.module.get_configuration_xml()

class PendingDataproviderWrapper(ModuleWrapper):
    def __init__(self, key):
        ModuleWrapper.__init__(
                    self,
                    "name", 
                    "description",
                    "gtk-missing",          #use a missing image
                    "twoway",               #twoway so can placehold as source or sink
                    "category", 
                    "in_type",
                    "out_type",
                    key.split(':')[0],
                    (),
                    None,                   #module is None. 
                    False)                  #enabled = False so a sync is not performed
        self.key = key
        self.xmltext = ""

    def get_key(self):
        return self.key

    def set_configuration_xml(self, xmltext):
        self.xmltext = xmltext

    def get_configuration_xml(self):
        return self.xmltext

    def __str__(self):
        return "PendingWrapper Key: %s" % self.get_key()


