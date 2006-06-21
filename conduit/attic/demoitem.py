# <![CDATA[
"""Demo item for DiaCanvas2.
"""
# vim:sw=4:et

# generators can be used to iterate shapes and child objects
from __future__ import generators

import gobject
import diacanvas
import diacanvas.shape as shape

class DemoItem(diacanvas.CanvasElement, diacanvas.CanvasAbstractGroup):

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
        # make the text a child of this canvas item
        self.add_construction(self.text)
        
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

gobject.type_register(DemoItem)
# add CanvasItem callbacks
diacanvas.set_callbacks(DemoItem)
# make the item groupable
diacanvas.set_groupable(DemoItem)

# end-of-file ]]>
