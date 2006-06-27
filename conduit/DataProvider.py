import gtk
import gobject
import goocanvas

import conduit

#WAS gsteditorelement
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
        #Should be overridden
        self.widget_color = "grey"
        self.widget_width = 100
        self.widget_height = 66
        
        #TODO: attach pad signals and events here
        #self.connect("button_press_event", self._onButtonPress)

    def onButtonPress(self, view, target, event, user_data_canvas):
        """
        Handle button clicks
        
        @param user_data: The canvas contating the popup item
        @type user_data: L{conduit.ConduitEditorCanvas.ConduitEditorCanvas}
        """
        print "Target = ",target
        print "View = ",view
        
        if event.type == gtk.gdk.BUTTON_PRESS:
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
            # Get the new position and move by the difference
            new_x = event.x
            new_y = event.y

            self.widget.translate(new_x - self.drag_x, new_y - self.drag_y)
            return True
            
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
            self.widget = goocanvas.Group()
            box = goocanvas.Rect(   x=0, 
                                    y=0, 
                                    width=self.widget_width, 
                                    height=self.widget_height,
                                    line_width=3, 
                                    stroke_color="black",
                                    fill_color=self.widget_color, 
                                    radius_y=5, 
                                    radius_x=5
                                    )
            text = goocanvas.Text(  x=int(self.widget_width/2), 
                                    y=int(self.widget_height/3), 
                                    width=80, 
                                    text=self.name, 
                                    anchor=gtk.ANCHOR_CENTER, 
                                    font="Sans 9"
                                    )
            image = goocanvas.Image(pixbuf=self.icon,
                                    x=int(  (self.widget_width/2) - 
                                            (self.icon.get_width()/2) ),
                                    y=int(  2*self.widget_height/3) - 
                                            (self.icon.get_height()/2) 
                                    )    
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
        self.widget_color = "blue"
  
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
        self.widget_color = "red"
 
        
        
