import diacanvas as dia
import gobject
import time

# A custom widget, Clock
class MyBox(dia.CanvasElement, dia.CanvasGroupable):
    def __init__(self):
        self.__gobject_init__()
        #dia.CanvasBox.__init__(self)
        #dia.CanvasGroupable.__init__(self)
        #contains a ellipse, and hour minute second hands
        self.ellipse = dia.shape.Ellipse()
        self.line = dia.shape.Path()
        #self.box = dia.shape.Box()

        #make the clock tick
        self.timeout_handler_id = gobject.timeout_add(1000, self.timer_handler)
        self.tick = 20

    def on_update (self,  affine):
        dia.CanvasElement.on_update (self, affine)
        self.ellipse.request_update() # request update, due to rotation

    def on_shape_iter (self):
        #for s in dia.CanvasBox.on_shape_iter(self):
        #    yield s
        yield self.ellipse
        yield self.line

    def on_point (self, x, y):
        """do nothing with this callback, it is used to determine the distance
        between the (mouse) cursor and the item. You may also ommit this
        callback, do the parent will automatically be called."""
        return dia.CanvasElement.on_point(self, x, y)

    def on_move (self, x, y, interactive):
        """The item is moved. Usually you don't have to override this one."""
        print 'move'
        return dia.CanvasElement.on_move(self, x, y, interactive);

    def on_handle_motion (self, handle, wx, wy, mask):
        """One of the item's handles has been moved."""
        return dia.CanvasElement.on_handle_motion(self, handle, wx, wy, mask);

    def on_glue (self, handle, wx, wy):
        ret = dia.CanvasElement.on_glue(self, handle, wx, wy);
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
# Set DiaCanvasItem specific callbacks for the GObject side of this class
# This only has to be done the first time you create a Python class based
# on a diacanvas.CanvasItem (DiaCanvasItem).
dia.set_callbacks(MyBox)
dia.set_groupable(MyBox)
