import gst
import gtk
import gobject
import goocanvas

#WAS gsteditorelement
class DataProviderModel(gobject.GObject):
    "DataProvider Model"
    
    def __init__(self, name=None, description=None):
        gobject.GObject.__init__(self)
        
        self.name = name
        self.description = description
        try:
            self.icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_OK, 48, 0)
        except gobject.GError, exc:
            print "can't load icon", exc

        #element.connect("element-added", self._elementAddedCb)
        #element.connect("element-removed", self._elementRemovedCb)
        
        #create widget 
        self.widget = goocanvas.Group()
        
        self.box = goocanvas.Rect(x=100, y=100, width=100, height=66,
                                    line_width=3, stroke_color="black",
                                    fill_color="grey", radius_y=5, radius_x=5)
        text = goocanvas.Text(x=150, y=133, width=80, text=description, 
                            anchor=gtk.ANCHOR_CENTER, font="Sans 9")
        self.widget.add_child(self.box)
        self.widget.add_child(text)
        #draw pads
        #self.pads = self._makePads()
        #self.hidePads()
        #self.widget.add_child(self.pads)
        #TODO: attach pad signals and events here
        #self.connect("button_press_event", self._onButtonPress)

    def _makeChannels(self):
        "Creates a Group containing individual channels"
        #TODO: color code based on the conduit used
        #TODO: each conduit connection point should get a widget added to this
        #       elements group. Do the connector repaint and move in python
        pgroup = goocanvas.Group()
        
        #set a creation callback so we can grab the view and set up callbacks
        pgroup.connect("child_added", self._onPadAdded)
        
        pgroup
        lefty = 109
        righty = 109
        leftx = 109
        rightx = 191
        #factory = self.element.get_factory()
        #numpads = factory.get_num_pad_templates()
        #print "total possible pad templates: " + str(numpads)
        #padlist = factory.get_static_pad_templates()
        plug = goocanvas.Ellipse(center_x = leftx, center_y = lefty,
                                        radius_x = 4, radius_y = 4,
                                        fill_color = "yellow", line_width = 2,
                                        stroke_color = "black")
        pgroup.add_child(plug)
        return pgroup
        
    def _onPadAdded(self, view, itemview, item):
        print "pad added"
        pass
    
    def hidePads(self):
        pass
        
    def showPads(self):
        pass

    def onButtonPress(self, view, target, event):
        "handle button clicks"
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 1:
                # Remember starting position for drag moves.
                self.drag_x = event.x
                self.drag_y = event.y
                return True

            elif event.button == 3:
                #TODO: pop up menu
                print "element popup"
                return True
            #TODO: double click to pop up element parameters window
        
    def onMotion(self, view, target, event):
        #drag move
        if event.state & gtk.gdk.BUTTON1_MASK:
            # Get the new position and move by the difference
            new_x = event.x
            new_y = event.y

            self.widget.translate(new_x - self.drag_x, new_y - self.drag_y)
            #TODO: for all in group .translate()
    
            return True
        
    def onEnter(self, view, target, event):
        "display the pads when mousing over"
        self.showPads()
        
    def onLeave(self, view, target, event): 
        "hide the pads when mousing out"
        self.hidePads()
    
    def _elementRemovedCb(self):
        raise NotImplementedError
        
    def get_icon(self):
        """
        Returns a GdkPixbuf hat represents this handler.
        Returns None if there is no associated icon.
        """
        return self.icon
        
    def deserialize(self, class_name, serialized):
        print "not implemented"
        #try:
        #	match = getattr(sys.modules[self.__module__], class_name)(self, **serialized)
        #	if match.is_valid():
        #		return match
        #except Exception, msg:
        #	print 'Warning:Error while deserializing match:', class_name, serialized, msg
        #return None

    def serialize(self, class_name):
        print "not implemented"
        
    def initialize(self):
        print "not implemented"        

    def addElement(self, element):
        print "not implemented"        
    
    def removeElement(self, element):
        print "not implemented"        
        

    # Callbacks from gst.Bin, update UI here
    # VIEW
        
    def _providerCommectedCb(self, bin, element):
        # create a ElementModel() to wrap the element added
        # display it
        raise NotImplementedError

    def _providerDisconnectedCb(self, bin, element):
        # find the widget associated with the element
        # remove it from UI
        raise NotImplementedError


class DataSource(DataProviderModel):
    """Base Class for DataSources
    """
    def __init__(self, name=None, description=None):
        DataProviderModel.__init__(self, name, description)
        try:
            self.icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_OK, 16, 0)
        except gobject.GError, exc:
            print "can't load icon", exc
        
     
class DataSink(DataProviderModel):
    """Base Class for DataSinks
    """
    def __init__(self, name=None, description=None):
        DataProviderModel.__init__(self, name, description)
        try:
            self.icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_NO, 16, 0)
        except gobject.GError, exc:
            print "can't load icon", exc
            

