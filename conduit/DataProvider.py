import gtk
import gobject
import goocanvas

import conduit


class DataProviderModel(gobject.GObject):
    """
    Model of a DataProvider. Can be a source or a sink
    
    @ivar name: The name of the module
    @type name: C{string}
    @ivar description: The name of the module
    @type description: C{string}
    @ivar widget: The name of the module
    @type widget: C{goocanvas.Group}
    @ivar widget_color: The background color of the base widget
    @type widget_color: C{string}    
    """
    
    def __init__(self, name=None, description=None):
        """
        Test
        """
        gobject.GObject.__init__(self)
        
        self.name = name
        self.description = description
        self.icon = None
        self.widget = None
        #The following can be overridden to customize the appearance
        #of the basic dataproviders
        self.icon_name = gtk.STOCK_OK        
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM2_LIGHT
        self.widget_width = 120
        self.widget_height = 80
        
    def get_icon(self):
        """
        Returns a GdkPixbuf hat represents this handler.
        """
        if self.icon is None:
            try:
                self.icon = gtk.icon_theme_get_default().load_icon(self.icon_name, 16, 0)
            except gobject.GError, exc:
                self.icon = None
                print >> stderr, "can't load icon", exc
        return self.icon
        
    def get_widget(self):
        """
        Returns the goocanvas item for drawing this widget on the canvas. 
        Subclasses may override this method to draw more custom widgets
        """
        #Create it the first time
        if self.widget is None:
            #use widget_color_rgba if specified
            #if self.widget_color_rgba is not None:
            #    print "pretty colors = ", self.widget_color_rgba
                
            self.widget = goocanvas.Group()
            box = goocanvas.Rect(   x=0, 
                                    y=0, 
                                    width=self.widget_width, 
                                    height=self.widget_height,
                                    line_width=3, 
                                    stroke_color="black",
                                    fill_color_rgba=self.widget_color_rgba, 
                                    radius_y=5, 
                                    radius_x=5
                                    )
            text = goocanvas.Text(  x=int(2*self.widget_width/5), 
                                    y=int(2*self.widget_height/3), 
                                    width=3*self.widget_width/5, 
                                    text=self.name, 
                                    anchor=gtk.ANCHOR_WEST, 
                                    font="Sans 8"
                                    )
            pb=self.get_icon()
            image = goocanvas.Image(pixbuf=pb,
                                    x=int(  
                                            (1*self.widget_width/5) - 
                                            (pb.get_width()/2) 
                                         ),
                                    y=int(  
                                            (2*self.widget_height/3) - 
                                            (pb.get_height()/2)
                                         )
                                             
                                    )
                                    
        
            #We need some way to tell the canvas that we are a dataprovider
            #and not a conduit
            self.widget.set_data("is_a_dataprovider",True)
            
            self.widget.add_child(box)
            self.widget.add_child(text)
            self.widget.add_child(image)
            
        return self.widget
        
    def get_widget_dimensions(self):
        """
        Returns the width of the DataProvider canvas widget.
        Should be overridden by those dataproviders which draw their own
        custom widgets
        
        @rtype: C{int}, C{int}
        @returns: width, height
        """
        return self.widget_width, self.widget_height
        
    def deserialize(self, class_name, serialized):
        """
        Deserialize
        """
        print "not implemented"
        #try:
        #	match = getattr(sys.modules[self.__module__], class_name)(self, **serialized)
        #	if match.is_valid():
        #		return match
        #except Exception, msg:
        #	print 'Warning:Error while deserializing match:', class_name, serialized, msg
        #return None

    def serialize(self, class_name):
        """
        Serialize
        """
        print "not implemented"
        
    def initialize(self):
        """
        Initialize
        """
        print "not implemented"
        
    def configure(self, window):
        """
        Show a configuration box for configuring the dataprovider instance
        
        @param window: The parent window (to show a modal dialog)
        @type window: {gtk.Window}
        """
        pass
        
    def put(self, data_type):
        """
        Stores data.
        This function must be overridden by the appropriate dataprovider. Its
        exact behavior is behavior is determined by the derived type.
        
        @param data_type: Data which to save
        @type data_type: A L{conduit.DataType.DataType} derived type that this 
        dataprovider is capable of handling
        @rtype: C{bool}
        @returns: True for success, false on failure
        """
        return False
        
    def get(self):
        """
        Returns all appropriate data.
        This function must be overridden by the appropriate dataprovider. Its
        exact behavior is behavior is determined by the derived type.
        
        @rtype: L{conduit.DataType.DataType}[]
        @returns: An array of all data needed for synchronization and provided
        through configuration by this dataprovider.
        """
        return None        

#Tango colors taken from 
#http://tango.freedesktop.org/Tango_Icon_Theme_Guidelines
TANGO_COLOR_BUTTER_LIGHT = int("fce94fff",16)
TANGO_COLOR_BUTTER_MID = int("edd400ff",16)
TANGO_COLOR_BUTTER_DARK = int("c4a000ff",16)
TANGO_COLOR_ORANGE_LIGHT = int("fcaf3eff",16)
TANGO_COLOR_ORANGE_MID = int("f57900",16)
TANGO_COLOR_ORANGE_DARK = int("ce5c00ff",16)
TANGO_COLOR_CHOCOLATE_LIGHT = int("e9b96eff",16)
TANGO_COLOR_CHOCOLATE_MID = int("c17d11ff",16)
TANGO_COLOR_CHOCOLATE_DARK = int("8f5902ff",16)
TANGO_COLOR_CHAMELEON_LIGHT = int("8ae234ff",16)
TANGO_COLOR_CHAMELEON_MID = int("73d216ff",16)
TANGO_COLOR_CHAMELEON_DARK = int("4e9a06ff",16)
TANGO_COLOR_SKYBLUE_LIGHT = int("729fcfff",16)
TANGO_COLOR_SKYBLUE_MID = int("3465a4ff",16)
TANGO_COLOR_SKYBLUE_DARK = int("204a87ff",16)
TANGO_COLOR_PLUM_LIGHT = int("ad7fa8ff",16)
TANGO_COLOR_PLUM_MID = int("75507bff",16)
TANGO_COLOR_PLUM_DARK = int("5c3566ff",16)
TANGO_COLOR_SCARLETRED_LIGHT = int("ef2929ff",16)
TANGO_COLOR_SCARLETRED_MID = int("cc0000ff",16)
TANGO_COLOR_SCARLETRED_DARK = int("a40000ff",16)
TANGO_COLOR_ALUMINIUM1_LIGHT = int("eeeeecff",16)
TANGO_COLOR_ALUMINIUM1_MID = int("d3d7cfff",16)
TANGO_COLOR_ALUMINIUM1_DARK = int("babdb6ff",16)
TANGO_COLOR_ALUMINIUM2_LIGHT = int("888a85ff",16)
TANGO_COLOR_ALUMINIUM2_MID = int("555753ff",16)
TANGO_COLOR_ALUMINIUM2_DARK = int("2e3436ff",16)

class DataSource(DataProviderModel):
    """
    Base Class for DataSources
    """
    def __init__(self, name=None, description=None):
        DataProviderModel.__init__(self, name, description)
        
        #customizations
        self.icon_name = gtk.STOCK_OK
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM1_MID
  
class DataSink(DataProviderModel):
    """
    Base Class for DataSinks
    """
    def __init__(self, name=None, description=None):
        #super fills in the name and description
        DataProviderModel.__init__(self, name, description)

        #customizations
        self.icon_name = gtk.STOCK_NO
        self.widget_color_rgba = TANGO_COLOR_SKYBLUE_LIGHT
 
        
        
