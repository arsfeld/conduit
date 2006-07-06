import gtk
import gobject
import goocanvas

import conduit

#WAS gsteditorelement
CONNECT_STATE_NONE = 0
CONNECT_STATE_START = 1
CONNECT_STATE_DRAG = 2
CONNECT_STATE_RELEASE = 3

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
        try:
            self.icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_OK, 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc
            

        self.widget = None
        #The following can be overridden to customize the appearance
        #of the basic dataproviders
        #self.widget_color = "grey"
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM2_LIGHT
        self.widget_width = 120
        self.widget_height = 80
        
        #manages the connection to other DataProviders
        self.connected_polylines = []
        #state machine for managing connecting to another DataProvider
        self.connect_state = CONNECT_STATE_NONE
        
        #TODO: attach pad signals and events here
        #self.connect("button_press_event", self._onButtonPress)

    def onButtonPress(self, view, target, event, user_data_canvas):
        """
        Handle button clicks
        
        @param user_data: The canvas contating the popup item
        @type user_data: L{conduit.ConduitEditorCanvas.ConduitEditorCanvas}
        """
        
        if event.type == gtk.gdk.BUTTON_PRESS:
            #tell the canvas we recieved the click (needed for cut, 
            #copy, past, configure operations
            user_data_canvas.selcted_dataprovider = self
            if event.button == 1:
                # Remember starting position for drag moves.
                self.drag_x = event.x
                self.drag_y = event.y
                return True

            elif event.button == 3:
                user_data_canvas.item_popup.popup(
                                            None, None, 
                                            None, event.button, event.time
                                            )
                return True
                
            #TODO: double click to pop up element parameters window
        
    def onMotion(self, view, target, event):
        """
        Handles dragging of items
        """
        #drag move
        if event.state & gtk.gdk.BUTTON1_MASK:
            if self.connect_state != CONNECT_STATE_START:
                #self.connect_state = CONNECT_STATE_DRAG
                #print "start state"
                # Get the new position and move by the difference
                new_x = event.x
                new_y = event.y

                self.widget.translate(new_x - self.drag_x, new_y - self.drag_y)

            return True
            
    def onEnter(self, view, target, event):
        #print "dp enter"
        pass
    
    def onLeave(self, view, target, event):
        #print "dp leave"
        pass
                        
    def onPadEnter(self, view, target, event):
        item = target.get_item()
        item.set_property("fill_color_rgba", TANGO_COLOR_CHOCOLATE_MID)
        #print "pad mouseover"
        
        
    def onPadLeave(self, view, target, event):
        item = target.get_item()
        item.set_property("fill_color_rgba", TANGO_COLOR_CHOCOLATE_DARK)
        #print "pad mouseout"
        
    def onPadPress(self, view, target, event):
        #print "pad clicked"
        #print "view = ", view
        #print "target = ", target
        #print "event = ", event
        #print "self = ", self
        if self.connect_state == CONNECT_STATE_NONE:
            self.connect_state = CONNECT_STATE_START
            print "start state"
            dapoints = goocanvas.Points([(event.x,event.y), (100,100)])
            pl = goocanvas.Polyline(points=dapoints,close_path=True)
            #self.connected_polylines.append(pl)
            #self.widget.add_child(pl)
        
    def onPadRelease(self, view, target, event):
        self.connect_state = CONNECT_STATE_NONE
        x = event.x
        y = event.y
        print "release", x           
            
    def get_icon(self):
        """
        Returns a GdkPixbuf hat represents this handler.
        """
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
            rect_w = 20
            rect_h = 20
            plug = goocanvas.Rect(  x=int(  (self.widget_width/2) - 
                                            (rect_w/2) ),
                                    y=int(  (rect_h/2) + 0), 
                                    width=rect_w, 
                                    height=rect_h,
                                    line_width=1, 
                                    stroke_color="black",
                                    fill_color_rgba=TANGO_COLOR_CHOCOLATE_DARK, 
                                    radius_y=3, 
                                    radius_x=3
                                    )
            #goocanvas.Ellipse(center_x = int(self.widget_width/2), 
            #                        center_y = int(self.widget_height/3),
            #                        radius_x = 8,
            #                        radius_y = 8,
            #                        fill_color = "yellow", 
            #                        line_width = 2,
            #                        stroke_color = "black"
            #                        )
            plug.set_data("item_type","pad")
            plug.set_data("pad","the pad")                                    
            text = goocanvas.Text(  x=int(2*self.widget_width/5), 
                                    y=int(2*self.widget_height/3), 
                                    width=3*self.widget_width/5, 
                                    text=self.name, 
                                    anchor=gtk.ANCHOR_WEST, 
                                    font="Sans 8"
                                    )
            image = goocanvas.Image(pixbuf=self.icon,
                                    x=int(  (1*self.widget_width/5) - 
                                            (self.icon.get_width()/2) ),
                                    y=int(  2*self.widget_height/3) - 
                                            (self.icon.get_height()/2) 
                                    )
                                    
        
            self.widget.add_child(box)
            self.widget.add_child(text)
            self.widget.add_child(image)
            self.widget.add_child(plug)       

            
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
        try:
            self.icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_OK, 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc
            
        #customize the color
        self.widget_color_rgba = TANGO_COLOR_ALUMINIUM1_MID
  
class DataSink(DataProviderModel):
    """
    Base Class for DataSinks
    """
    def __init__(self, name=None, description=None):
        #super fills in the name and description
        DataProviderModel.__init__(self, name, description)
        try:
            self.icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_NO, 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc
            
        #customize the color
        #self.widget_color = "red"
        self.widget_color_rgba = TANGO_COLOR_SKYBLUE_LIGHT
 
        
        
