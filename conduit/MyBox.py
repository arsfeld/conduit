import diacanvas
import gobject
import time

# A custom widget, Clock
class MyBox(diacanvas.CanvasElement, diacanvas.CanvasGroupable):
    def __init__(self):
        self.__gobject_init__()
        #diacanvas.CanvasBox.__init__(self)
        #diacanvas.CanvasGroupable.__init__(self)
        #contains a ellipse, and hour minute second hands
        self.ellipse = diacanvas.shape.Ellipse()
        self.line = diacanvas.shape.Path()
        #self.box = diacanvas.shape.Box()

        #make the clock tick
        self.timeout_handler_id = gobject.timeout_add(1000, self.timer_handler)
        self.tick = 20

    def on_update (self,  affine):
        diacanvas.CanvasElement.on_update (self, affine)
        self.ellipse.request_update() # request update, due to rotation

    def on_shape_iter (self):
        #for s in diacanvas.CanvasBox.on_shape_iter(self):
        #    yield s
        yield self.ellipse
        yield self.line

    def on_point (self, x, y):
        """do nothing with this callback, it is used to determine the distance
        between the (mouse) cursor and the item. You may also ommit this
        callback, do the parent will automatically be called."""
        return diacanvas.CanvasElement.on_point(self, x, y)

    def on_move (self, x, y, interactive):
        """The item is moved. Usually you don't have to override this one."""
        print 'move'
        return diacanvas.CanvasElement.on_move(self, x, y, interactive);

    def on_handle_motion (self, handle, wx, wy, mask):
        """One of the item's handles has been moved."""
        return diacanvas.CanvasElement.on_handle_motion(self, handle, wx, wy, mask);

    def on_glue (self, handle, wx, wy):
        ret = diacanvas.CanvasElement.on_glue(self, handle, wx, wy);
        return ret


    def timer_handler(self):
        print 'tick = ' + str(self.tick)
        self.tick = self.tick+2
        self.ellipse.ellipse (center=(20,20), width=self.tick, height=20)
        self.ellipse.set_line_width(1)
        self.ellipse.request_update()

        return True

    # CanvasGroupable
    def on_groupable_add (self, item):
        '''This function is only used to add child items during construction.'''
        return 0

# Create a GObject type for this item:
gobject.type_register(MyBox) 
diacanvas.set_callbacks(MyBox)
diacanvas.set_groupable(MyBox)

import diacanvas.shape as shape
class MyBox2(diacanvas.CanvasElement, diacanvas.CanvasAbstractGroup):
    def __init__(self):
        self.__gobject_init__()

        # create our line shapes (a red and a green line)
        self.top_line = shape.Path()
        self.top_line.set_color(diacanvas.color(255, 0, 0))
        self.top_line.set_line_width(2)
        self.bottom_line = shape.Path()
        self.bottom_line.set_color(diacanvas.color(0, 255, 0))
        self.bottom_line.set_line_width(2)
        
        # create a text object (CanvasText is a composite object)
        self.text = diacanvas.CanvasText()
        self.text.set(text="hello")
        # make the text a child of this canvas item
        self.text.set_child_of(self)
        #self.add_construction(self.text)
        
    def on_update(self, affine):
        # create a line on the top
        # (line() takes one argument: a list of points)
        self.top_line.line([(0, 0), (self.width, 0)])

        # create a line on the bottom
        self.bottom_line.line([(0, self.height), (self.width, self.height)])

        # give the text the same width and height as out object
        self.text.set(width=self.width, height=self.height)
        
        # update the text
        self.update_child(self.text, affine)

        # update the parent
        diacanvas.CanvasElement.on_update(self, affine)

        # expand the boundries of this canvas item so the lines (with
        # width 2.0) are inside the boundries of this canvas item.
        self.expand_bounds(1.0)

    def on_shape_iter(self):
        # an iterator 
        yield self.top_line
        yield self.bottom_line
        # alternative:
        #return iter([self.top_line, self.bottom_line])

    def on_event(self, event):
        # make sure key events are send to our text object
        if event.type == diacanvas.EVENT_KEY_PRESS:
            print 'key'
            self.text.focus()
            return self.text.on_event(event)
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
        """Return an iterator that can be used to traverse the children.
        """
        yield self.text
        # alternative:
        # return iter([self.text])

    def on_groupable_length(self):
        """Return the number of child objects, we have just the text object.
        """
        return 1

    def on_groupable_pos(self, item):
        """Return the position of the item wrt other child objects.
        (we have only one child).
        """
        if item == self.text:
            return 0
        else:
            return -1

gobject.type_register(MyBox2)
# add CanvasItem callbacks
diacanvas.set_callbacks(MyBox2)
# make the item groupable
diacanvas.set_groupable(MyBox2)

class MyBox3(diacanvas.CanvasElement, diacanvas.CanvasAbstractGroup):
    def __init__(self):
        self.__gobject_init__()

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

        self.h = diacanvas.Handle(self)
        self.h.set_property('connectable',True)
        self.h.set_property('movable',False)

        
        # create a text object (CanvasText is a composite object)
        #self.text = diacanvas.CanvasText()
        #self.text.set(text="hello")
        # make the text a child of this canvas item
        #self.text.set_child_of(self)
        #self.add_construction(self.text)
        
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
        #self.text.set(width=self.width, height=self.height)
        
        # update the text
        #self.update_child(self.text, affine)

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

    #def on_groupable_iter(self):
    #    """Return an iterator that can be used to traverse the children.
    #    """
    #    #yield self.text
    #    # alternative:
    #    # return iter([self.text])

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

gobject.type_register(MyBox3)
# add CanvasItem callbacks
diacanvas.set_callbacks(MyBox3)
# make the item groupable
diacanvas.set_groupable(MyBox3)
