# vim: sw=4:et:
"""PlacementTool

Tool used to place objects on the canvas.

This class overrules the Placement tool that is coded in the diacanvas C code.
Since we can not instantiate Python objects from the C implementation.
"""

__all__ = [ 'PlacementTool' ]

__author__ = 'Arjan J. Molenaar'
__revision__ = '$revision$'
__date__ = '$date$'

import gobject
import traceback
import gtk.gdk as gdk
import diacanvas

class PlacementTool(diacanvas.view.Tool):
    __gsignals__ = {
        'button_press_event': 'override',
        'button_release_event': 'override',
        'motion_notify_event': 'override'
    }

    def __init__(self, type, **properties):
        self.__gobject_init__()
        self.type = type
        self.properties = properties

    def print_error(self, msg, exc=None):
        print type(self).__name__, ':', msg
        traceback.print_exc()

    def do_button_press_event(self, view, event):
        #old_allow_undo = view.canvas.get_property ('allow_undo')
        #view.canvas.set_property ('allow_undo', 0)
        
        #cursor = gdk.Cursor(gdk.WATCH)
        #gdk.pointer_grab(window=view.window, cursor=cursor)

        try:
            self.new_object = self._create_item(view, event)
        except Exception, e:
            self.print_error('Error while creating new item', e)
            self.new_object = None
            return True

        if not self.new_object:
            return True

        if not self.new_object.parent:
            self.new_object.set_property('parent', view.canvas.root)

        try:
            self._move_item(view, event, self.new_object)
        except Exception, e:
            self.print_error('Error while moving new item', e)
            self.new_object.parent.remove(self.new_object)
            self.new_object = None
            return True

        view.unselect_all()
        view_item = view.find_view_item(self.new_object)
        view.focus(view_item)

        try:
            self._grab_handle(view, event, self.new_object)
        except Exception, e:
            self.print_error('Error while grabbing new item', e)
            self.new_object.parent.remove(self.new_object)
            self.new_object = None
            return True

        return True

    def do_button_release_event(self, view, event):
        try:
            self.handle_tool.button_release(view, event)
            del self.handle_tool
        except AttributeError:
            pass
        del self.new_object
        return False

    def do_motion_notify_event(self, view, event):
        try:
            self.handle_tool.motion_notify(view, event)
        except AttributeError, e:
            pass

    def _create_item(self, view, event):
        """Create a new object to be added to the canvas.
        Return: new canvas item.
        """
        item = self.type()
        if self.properties and len(self.properties) > 0:
            try:
                for (k,v) in self.properties.items():
                    item.set_property(k, v)
            except TypeError, e:
                self.print_error('Could not set properties', e)
        return item
        
    def _move_item(self, view, event, item):
        """Move the newly created item to the desired position.
        """
        #wx, wy = view.window_to_world(event.x, event.y)
        #ix, iy = item.affine_point_w2i(wx, wy)
        ix, iy = item.affine_point_w2i(event.x, event.y)
        item.move(ix, iy)
        
    def _grab_handle(self, view, event, item):
        """Grab a handle of the newly created canvas item. This will allow
        the user to instanty resize the newly created canvas item.
        """
        self.handle_tool = diacanvas.view.HandleTool()
        if isinstance(item, diacanvas.CanvasLine) and len(item.handles) > 0:
            first = item.handles[0]
            last = item.handles[-1]
            wx, wy = view.window_to_world(event.x, event.y)

            #import sys
            #print view.canvas.root.children[0], sys.getrefcount(view.canvas.root.children[0])
            dist, glue, glue_to = view.canvas.glue_handle (first, wx, wy)
            #print glue_to, sys.getrefcount(glue_to)

            if glue_to and (dist <= self.handle_tool.glue_distance):
                # before connection determine point, which handle should
                # point to
                d, (x, y) = glue_to.on_glue(first, wx, wy)
                first.set_pos_w(float(x), float(y))
                glue_to.connect_handle(first)
            self.handle_tool.set_grabbed_handle(last)
        elif isinstance(item, diacanvas.CanvasElement):
            #print 'PlacementTool: setting handle of Element'
            handle = item.handles[diacanvas.HANDLE_SE]
            if handle.get_property('movable'):
                self.handle_tool.set_grabbed_handle(handle)
        else:
            self.print_error('No handle handling for element %s' % item)

# No longer needed for PyGTK 2.8 +
#gobject.type_register(PlacementTool)
