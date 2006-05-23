import sys
import diacanvas
import diacanvas.shape as shape
import gtk, gobject
import conduit, Utils

class DataProvider(diacanvas.CanvasElement, diacanvas.CanvasGroupable):
    def __init__(self):
        self.__gobject_init__()
        
        
        self.icon = Utils.load_icon("gtk-file")
        print "icon = " + str(self.icon)
        self.image = diacanvas.shape.Image()
        self.image.image(self.icon)
             
        self.word = "Base"

        # create our line shapes (a red and a green line)
        self.top_line = shape.Path()
        self.top_line.set_color(diacanvas.color(255, 0, 0))
        self.top_line.set_line_width(2)
        self.bottom_line = shape.Path()
        self.bottom_line.set_color(diacanvas.color(0, 255, 0))
        self.bottom_line.set_line_width(2)
        self.ellipse = shape.Ellipse()
        self.ellipse.set_color(diacanvas.color(0, 0, 255))
        self.ellipse.set_line_width(2)
        #handle to grab onto
        self.h = diacanvas.Handle(self)
        self.h.set_property('connectable',True)
        self.h.set_property('movable',False)
        # create a text object (CanvasText is a composite object)
        self.text = diacanvas.CanvasText()
        # make the text a child of this canvas item
        self.text.set_child_of(self)
        #self.add_construction(self.text)
    
    #---------- diacanvas.CanvasElement ----------    
    def on_update(self, affine):
        # create a line on the top
        # (line() takes one argument: a list of points)
        self.top_line.line([(0, 0), (self.width, 0)])

        # create a line on the bottom
        self.bottom_line.line([(0, self.height), (self.width, self.height)])

        # Draw the ellipse in the middle
        self.ellipse.ellipse(center=(self.width/2,self.height/2), width=self.width/4, height=self.height/4)

        # move the handle to the middle
        self.h.set_pos_i(self.width/2,self.height/2)

        # give the text the same width and height as out object
        self.text.set(width=self.width, height=self.height)
        
        # update the text
        self.text.set(text=self.word)
        self.update_child(self.text, affine)

        self.image.set_pos([self.width/2,self.height/2])

        # update the parent
        diacanvas.CanvasElement.on_update(self, affine)

        # expand the boundries of this canvas item so the lines (with
        # width 2.0) are inside the boundries of this canvas item.
        self.expand_bounds(1.0)

    def on_shape_iter(self):
        # an iterator 
        yield self.top_line
        yield self.bottom_line
        yield self.ellipse
        yield self.image
        # alternative:
        #return iter([self.top_line, self.bottom_line])

    def on_event(self, event):
        # make sure key events are send to our text object
        if event.type == diacanvas.EVENT_KEY_PRESS:
            print 'key'
        #    self.text.focus()
        #    return self.text.on_event(event)
        else:
            return diacanvas.CanvasElement.on_event(self, event)

    # Groupable

    def on_groupable_add(self, item):
        """Add a new item. This is not allowed in this case.
        """
        return 0

    def on_groupable_remove(self, item):
        """Do not allow the text to be removed.
        """
        return 1

    def on_groupable_iter(self):
        """
        Return an iterator that can be used to traverse the children.
        """
        yield self.text
        #alternative:
        #return iter([self.text])

    def on_groupable_length(self):
        """Return the number of child objects, we have just the text object.
        """
        return 1

    def on_groupable_pos(self, item):
        """Return the position of the item wrt other child objects.
        (we have only one child).
        """
        #if item == self.text:
        #    return 0
        #else:
        #    return -1
        return -1
   
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
		
    def get_icon(self):
        """
        Returns a GdkPixbuf hat represents this handler.
        Returns None if there is no associated icon.
        """
        return self._icon
	
# Create a GObject type for this item:
#if gtk.pygtk_version < (2,8,0):
gobject.type_register(DataProvider)
#subclasses do not need to do this.
diacanvas.set_callbacks(DataProvider)
#subclasses do need to do this
diacanvas.set_groupable(DataProvider)
