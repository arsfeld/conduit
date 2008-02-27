import traceback
import logging
log = logging.getLogger("ModuleWrapper")

class ModuleWrapper: 
    """
    A generic wrapper for any dynamically loaded module. Wraps the complexity
    of a stored L{conduit.DataProvider.DataProvider} behind additional
    descriptive fields like name and description. Useful for classification 
    and searching for moldules of certain types, etc.
    """
    
    NUM_UID_DIGITS = 5
    COMPULSORY_ATTRIBUTES = [
                            "type"
                            ]
    	
    def __init__ (self, **kwargs):
        """
        Constructor for ModuleWrapper. A convenient wrapper around a dynamically
        loaded module.
        
        @keyword name: The name of the contained module
        @keyword description: The description of the contained module
        @keyword icon_name: The name of an icon representing the contained module
        @keyword module_type: The type of the contained module (e.g. sink, source)
        @keyword category: The category of the contained module
        @keyword in_type: The name of the datatype that the module accepts (put())
        @keyword out_type: The name of the datatype that the module produces (get())
        @keyword filename: The filename from which the module was loaded
        @keyword classname: The classname used to instanciate another module instance
        @keyword initargs: The arguments passed to the new module if created
        @keyword module: An instance of the described module
        @keyword loaded: Whether the module was loaded corectly 
        """
        self.name =                 kwargs.get("name","")
        self.description =          kwargs.get("description","")
        self.icon_name =            kwargs.get("icon_name","image-missing")
        self.module_type =          kwargs.get('module_type',"twoway")
        self.category =             kwargs.get('category',"")
        self.in_type =              kwargs.get('in_type',"")
        self.out_type =             kwargs.get('out_type',"")
        self.filename =             kwargs.get('filename',"")
        self.classname =            kwargs.get('classname',"")
        self.initargs =             kwargs.get('initargs',())
        self.module =               kwargs.get('module',None)
        self.enabled =              kwargs.get('enabled',True)

        #Initargs must be a tuple or a list for get_key() to work
        if type(self.initargs) != tuple:
            log.warn("init args must be a tuple (was:%s type:%s)" % (self.initargs,type(self.initargs)))
            raise Exception
        
        self.icon_path = ""
        self.icon = {}
        self.descriptiveIcon = None

    def __str__(self):
        return "Wrapper: %s %s (UID: %s)" % (self.get_name(), self.module_type, self.get_UID())

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
            
    def get_name(self):
        """
        @returns: The dataproviders user readable name
        """
        if self.module == None:
            return self.name
        else:
            return self.module.get_name()
        
    def set_name(self, name):
        """
        Sets the dataproviders user readable name
        """
        self.name = name
       
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

    def get_input_type(self):
        """
        Returns the in_type for the module. If the module has not yet been 
        initialised then its in_type is derived from its class attributes. 
        If it has been initialised then it can supply its own in_type
        """
        if self.module == None:
            return self.in_type
        else:
            return self.module.get_input_type()

    def get_output_type(self):
        """
        Returns the out_type for the module. See get_input_type()
        """
        if self.module == None:
            return self.out_type
        else:
            return self.module.get_output_type()


    def get_icon(self, size=16):
        """
        Returns the icon for the module contained in this wrapper.
        In the case of a sink or source this is easy as the module
        contains the icon.

        Wrappers derived from this class (such as the CategoryWrapper)
        may override this function
        """
        import gtk
        if not self.icon.has_key(size) or self.icon[size] is None:
            if self.module_type in ["source", "sink", "twoway", "category"]:
                try:
                    info = gtk.icon_theme_get_default().lookup_icon(self.icon_name, size, 0)
                    self.icon[size] = info.load_icon()
                    self.icon_path = info.get_filename()
                except:
                    self.icon[size] = None
                    log.warn("Could not load icon %s for %s" % (self.icon_name, self.name))
                    #Last resort: Try the non icon-naming-spec compliant icon
                    self.icon_name = "conduit"
                    info = gtk.icon_theme_get_default().lookup_icon(self.icon_name, size, 0)
                    self.icon[size] = info.load_icon()
                    self.icon_path = info.get_filename()

        return self.icon[size]

    def get_descriptive_icon(self):
        """
        The descriptive icon is two icons composited side by side. On the left
        is the dataprovider icon, on the right an arrow indicating its type
        size of each icon
        """
        import gtk

        #  _____
        # |     |___
        # |  i  | a |
        # |_____|___|
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
                    log.warn("Error getting icon\n%s" % traceback.format_exc())
            
            elif self.module_type == "category":
                self.descriptiveIcon = self.get_icon(isize)
    
        return self.descriptiveIcon
        
    def set_configuration_xml(self, xmltext):
        self.module.set_configuration_xml(xmltext)

    def get_configuration_xml(self):
        return self.module.get_configuration_xml()

    def configure(self, window):
        self.module.configure(window)

class PendingDataproviderWrapper(ModuleWrapper):
    def __init__(self, key):
        ModuleWrapper.__init__(
                    self,
                    module_type="twoway",
                    classname=key.split(':')[0],
                    module=None,
                    enabled=False
                    )
        self.key = key
        self.xmltext = ""

    def __str__(self):
        return "PendingWrapper Key: %s" % self.get_key()

    def get_key(self):
        return self.key

    def set_configuration_xml(self, xmltext):
        self.xmltext = xmltext

    def get_configuration_xml(self):
        return self.xmltext


