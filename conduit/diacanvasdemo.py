#!/usr/bin/env python2.2
# vim:sw=4:et:

from __future__ import generators

import pygtk
pygtk.require('2.0')
  
import sys, gc, weakref

import gobject
import gtk
import pango
import diacanvas as dia
from placementtool import *
import demoitem

class MyText(dia.CanvasText):

    def __init__(self):
        self.__gobject_init__()

gobject.type_register(MyText)


# A custom widget, testing callback inheritance
class MyBox(dia.CanvasBox, dia.CanvasGroupable):

    def __init__(self):
	self.__gobject_init__() # default constructor using our new GType
	# We add an ellipse *shape* to our new Box.
	self.ellipse = dia.shape.Ellipse()
	self.ellipse.ellipse (center=(20,20), width=20, height=20)
	self.ellipse.set_line_width (1)
	def text_changed(text_item, shape, text, me):
	    print text_item, shape, text, me
	#self.text = dia.CanvasText()
	self.text = dia.CanvasText() #MyText()
	self.text.set_child_of(self) # do child -> parent mapping
	self.text.connect('text_changed', text_changed, self)
	font = pango.FontDescription('sans 20')
	self.text.set(text='hello', font=font, width=self.width - 20, height=40)
	print 'Added,\tself =', self
	print '\tself.text.parent =', self.text.parent
	print '\tself.text.canvas =', self.text.canvas
	self.text.move(10, 30)
	print 'done'

    def do_update (self,  affine):
        print 'do_update(' + str(self) + ', ' + str(affine) + ')'

    def on_shape_iter (self):
	for s in dia.CanvasBox.on_shape_iter(self):
            yield s
	if self.is_selected():
            yield self.ellipse

    def do_point (self, x, y):
	"""do nothing with this callback, it is used to determine the distance
	between the (mouse) cursor and the item. You may also ommit this
	callback, do the parent will automatically be called."""
	return dia.CanvasBox.do_point(self, x, y)

    def do_move (self, x, y, interactive):
	"""The item is moved. Usually you don't have to override this one."""
	return dia.CanvasBox.do_move(self, x, y, interactive);

    def do_handle_motion (self, handle, wx, wy, mask):
	"""One of the item's handles has been moved."""
	return dia.CanvasBox.do_handle_motion(self, handle, wx, wy, mask);

    def do_glue (self, handle, wx, wy):
	#print 'do_glue(' + str(self) +  ', ' + str(handle) + ', ' + str(wx) + ', ' + str(wy) + ')'
	ret = dia.CanvasBox.do_glue(self, handle, wx, wy);
	#print 'do_glue: ret =', ret
	return ret
        
#    def on_event (self, event):
#	#print 'on_event(' + str(self) +  ', ' + str(event) + ')'
#	ret = dia.CanvasBox.on_event(self, event);
#	#print 'on_event: ret =', ret
#	return ret

#    def on_connect_handle (self, handle):
#	print 'on_connect_handle(' + str(self) +  ', ' + str(handle) + ')'
#	ret = dia.CanvasBox.on_connect_handle(self, handle);
#	print 'on_connect_handle: ret =', ret
#	return ret

#    def on_disconnect_handle (self, handle):
#	print 'on_disconnect_handle(' + str(self) +  ', ' + str(handle) + ')'
#	ret = dia.CanvasBox.on_disconnect_handle(self, handle);
#	print 'on_disconnect_handle: ret =', ret
#	return ret

    # CanvasGroupable
    def on_groupable_add (self, item):
	'''This function is only used to add child items during construction.'''
	#if not hasattr(self, 'text'):
	#    self.text = item
	#    return 1
	return 0

    def on_groupable_remove (self, item):
        pass

    def on_groupable_iter (self):
	if self.text:
	    yield self.text

    def on_groupable_length (self):
        return 1

    def on_groupable_pos (self, item):
        if item == self.text:
	    return 0
	else:
	    return -1

# Create a GObject type for this item:
gobject.type_register (MyBox) 
# Set DiaCanvasItem specific callbacks for the GObject side of this class
# This only has to be done the first time you create a Python class based
# on a diacanvas.CanvasItem (DiaCanvasItem).
dia.set_callbacks (MyBox)
dia.set_groupable (MyBox)

print 'Defining class MyBox2...'

class MyBox2(MyBox):
    def __init__(self):
	MyBox.__init__(self)
	self.text.set(text='Bye')

gobject.type_register (MyBox2) 
# dia.set_{callbacks|groupable} doesn't have to be called the second time.

FILE_NEW = 0
FILE_CLOSE = 1
FILE_QUIT = 2
EDIT_UNDO = 10
EDIT_REDO = 11
EDIT_SELECT_ALL = 12
EDIT_DEL_FOCUSED = 13
EDIT_DEL_SELECTED = 14
EDIT_GC = 15
VIEW_ZOOM_IN = 20
VIEW_ZOOM_OUT = 21
VIEW_ZOOM_100 = 22
VIEW_SNAP_TO_GRID = 23
VIEW_EDIT_GRID = 24
VIEW_NEW_AA_VIEW = 25
VIEW_NEW_X_VIEW = 26
OBJECT_ADD_LINE = 30
OBJECT_ADD_BOX = 31
OBJECT_ADD_DEMO_ITEM = 32
OBJECT_RESET = 33
LINE_ADD_POINT = 40
LINE_ADD_SEGMENT = 41
LINE_DEL_SEGMENT = 42

def mainquit (*arg):
    gtk.main_quit()

def unset_tool (tool, view, event, data):
    view.set_tool (None)
    #tool.disconnect (tool.signal_id)

def menu_item_cb (view, action, widget):
    print 'Action:', action, gtk.item_factory_path_from_widget(widget), view
    view.canvas.push_undo (None)

    if action == FILE_NEW:
        canvas = dia.Canvas()
	canvas.set_property ('allow_undo', 1)
    	view = dia.CanvasView(canvas=canvas, aa=1)
	display_canvas_view (view)
    elif action == FILE_CLOSE:
        view.get_toplevel().destroy()
    elif action == FILE_QUIT:
        view.get_toplevel().destroy()
        gtk.main_quit()
    elif action == EDIT_UNDO:
        view.canvas.pop_undo()
    elif action == EDIT_REDO:
        view.canvas.pop_redo()
    elif action == EDIT_SELECT_ALL:
        view.select_rectangle ( [ -100000, -100000, 100000, 100000 ] )
    elif action == EDIT_DEL_FOCUSED:
        if view.focus_item:
	    item = view.focus_item.item
	    # If the item is a composite item, remove the parent item instead
	    while (item.flags & dia.COMPOSITE) != 0:
	        item = item.parent
	    item.parent.remove (item)
    elif action == EDIT_DEL_SELECTED:
        pass # need wrapper
    elif action == EDIT_GC:
        gc.collect ()
    elif action == VIEW_ZOOM_IN:
        view.set_zoom (view.get_zoom() + 0.1)
    elif action == VIEW_ZOOM_OUT:
        view.set_zoom (view.get_zoom() - 0.1)
    elif action == VIEW_ZOOM_100:
        view.set_zoom (1.0)
    elif action == VIEW_SNAP_TO_GRID:
        snap = view.canvas.get_property ('snap_to_grid')
	view.canvas.set_property ('snap_to_grid', not snap)
    elif action == OBJECT_ADD_LINE:
        tool = PlacementTool (dia.CanvasLine, color=dia.color(220, 0, 0))
	view.set_tool (tool)
        tool.signal_id = tool.connect ('button_release_event', unset_tool, view)
    elif action == OBJECT_ADD_BOX:
        tool = PlacementTool (dia.CanvasBox, width=0.0, height=0.0)
	view.set_tool (tool)
        tool.signal_id = tool.connect ('button_release_event', unset_tool, view)
    elif action == OBJECT_ADD_DEMO_ITEM:
        tool = PlacementTool (demoitem.DemoItem, width=50.0, height=50.0)
	view.set_tool (tool)
        tool.signal_id = tool.connect ('button_release_event', unset_tool, view)
    else:
        print 'This item is not yet implemented.'

menu_items = (
    ('/_File', None, None, 0, '<Branch>' ),
    ('/File/_New', '<control>N', menu_item_cb, 0, ''),
    ('/File/_Close', None, menu_item_cb, FILE_CLOSE, ''),
    ('/File/sep1', None, None, 0, '<Separator>'),
    ('/File/_Quit', '<control>Q', menu_item_cb, FILE_QUIT, ''),

    ( '/_Edit', None, None, 0, '<Branch>' ),
    ( '/Edit/_Undo', '<control>Z', menu_item_cb, EDIT_UNDO ),
    ( '/Edit/_Redo', '<control>R', menu_item_cb, EDIT_REDO ),
    ( '/Edit/sep1', None, None, 0, '<Separator>' ),
    ( '/Edit/Select _All', '<control>A', menu_item_cb, EDIT_SELECT_ALL ),
    ( '/Edit/sep2', None, None, 0, '<Separator>' ),
    ( '/Edit/Delete f_Ocused', None, menu_item_cb, EDIT_DEL_FOCUSED ),
    ( '/Edit/Delete _Selected', '<control>D', menu_item_cb, EDIT_DEL_SELECTED ),
    ( '/Edit/sep3', None, None, 0, '<Separator>' ),
    ( '/Edit/_Garbage Collect', None, menu_item_cb, EDIT_GC ),

    ( '/_View', None, None, 0, '<Branch>' ),
    ( '/View/Zoom _In', None, menu_item_cb, VIEW_ZOOM_IN ),
    ( '/View/Zoom _Out', None, menu_item_cb, VIEW_ZOOM_OUT ),
    ( '/View/_Zoom 100%', None, menu_item_cb, VIEW_ZOOM_100 ),
    ( '/View/sep1', None, None, 0, '<Separator>' ),
    ( '/View/_Snap to grid', None, menu_item_cb, VIEW_SNAP_TO_GRID, '<ToggleItem>' ),
    ( '/View/Edit _Grid', None, menu_item_cb, VIEW_EDIT_GRID ),
    ( '/View/sep2', None, None, 0, '<Separator>' ),
    ( '/View/New _AA view', None, menu_item_cb, VIEW_NEW_AA_VIEW ),
    ( '/View/New _X view', None, menu_item_cb, VIEW_NEW_X_VIEW ),

    ( '/_Object', None, None, 0, '<Branch>' ),
    ( '/Object/Add _Line', None, menu_item_cb, OBJECT_ADD_LINE ),
    ( '/Object/Add _Box', None, menu_item_cb, OBJECT_ADD_BOX ),
    ( '/Object/Add _Demo Item', None, menu_item_cb, OBJECT_ADD_DEMO_ITEM ),
    ( '/Object/sep1', None, None, 0, '<Separator>' ),
    ( '/Object/_Untransform focused', None, menu_item_cb, OBJECT_RESET ),

    ( '/_Line', None, None, 0, '<Branch>' ),
    ( '/Line/Add point', None, menu_item_cb, LINE_ADD_POINT ),
    ( '/Line/Add 2nd segment', None, menu_item_cb, LINE_ADD_SEGMENT ),
    ( '/Line/Delete 2nd segment', None, menu_item_cb, LINE_DEL_SEGMENT )
)

item_factory = None
def display_canvas_view(view):
    global item_factory
    view.set_scroll_region(0.0, 0.0, 600.0, 450.0)
    win = gtk.Window()
    win.connect ('destroy', mainquit)
    win.set_title ('DiaCanvas Python example')
    win.set_default_size (400, 400)
    
    vbox = gtk.VBox(homogeneous=False)
    win.add (vbox)
    vbox.show()

    accelgroup = gtk.AccelGroup()
    win.add_accel_group(accelgroup)

    item_factory = gtk.ItemFactory(gtk.MenuBar, '<main>', accelgroup)
    item_factory.create_items(menu_items, view)

    menubar = item_factory.get_widget('<main>')
    vbox.pack_start(menubar, False, False, 0)
    menubar.show()

    table = gtk.Table(2,2, False)
    table.set_row_spacings (4)
    table.set_col_spacings (4)
    vbox.pack_start (table)
    table.show()

    frame = gtk.Frame()
    frame.set_shadow_type (gtk.SHADOW_IN)
    table.attach (frame, 0, 1, 0, 1,
		  gtk.EXPAND | gtk.FILL | gtk.SHRINK,
		  gtk.EXPAND | gtk.FILL | gtk.SHRINK)
    frame.show()

#    view.set_usize(600, 450)
    frame.add (view)
    view.show()
    
    sbar = gtk.VScrollbar (view.get_vadjustment())
    table.attach (sbar, 1, 2, 0, 1, gtk.FILL,
		  gtk.EXPAND | gtk.FILL | gtk.SHRINK)
    sbar.show()

    sbar = gtk.HScrollbar (view.get_hadjustment())
    table.attach (sbar, 0, 1, 1, 2, gtk.EXPAND | gtk.FILL | gtk.SHRINK,
		  gtk.FILL)
    sbar.show()

    win.show()

def connect_cb(self, handle):
    print 'A Handle has been connected'


rect = (0, 0, 1000, 1000)

canvas = dia.Canvas()

box = dia.CanvasBox()
box.set(parent=canvas.root, width=100, height=100)#, color=0x999900FF)
box.move (50, 50)
box.connect('connect', connect_cb)

line = dia.CanvasLine()
line.set(parent=canvas.root, add_point=(100, 100), color=dia.color(0, 200, 0))
line.set(add_point=(300, 300))

del box
del line

print '----------======------------'
my_box = MyBox()
#assert sys.getrefcount(my_box) == 3, '1: sys.getrefcount(my_box) == %d' % sys.getrefcount(my_box)

canvas.root.add(my_box)
#print 'Added,\troot =', canvas.root, '\n\tparent =', my_box.parent, '\n\tcanvas =', my_box.canvas
#print 'Added,\tparent =', my_box.text.parent, '\n\tcanvas =', my_box.text.canvas
#print 'references:', sys.getrefcount(my_box), my_box.__grefcount__
#assert sys.getrefcount(my_box) == 3, '2: sys.getrefcount(my_box) == %d' % sys.getrefcount(my_box)
#assert my_box.__grefcount__ == 2, '3: my_box.__grefcount__ == 2'
w_my_box = weakref.ref(my_box)
#w_my_box_dict = weakref.ref(my_box.__dict__)
#assert sys.getrefcount(my_box.__dict__) == 2
print 'my_box.__dict__ =', my_box.__dict__

del my_box
#assert sys.getrefcount(w_my_box()) == 2, '4: sys.getrefcount(w_my_box()) == %d' % sys.getrefcount(my_box)
#assert w_my_box().__grefcount__ == 2, '5: w_my_box().__grefcount__ == 2'
print 'w_my_box().__dict__ =', w_my_box().__dict__
assert hasattr(w_my_box(), 'ellipse'), '6: hasattr(w_my_box(), \'ellipse\')'

gc.collect()

#assert sys.getrefcount(w_my_box()) == 2, '7: sys.getrefcount(w_my_box()) == 2'
#assert w_my_box().__grefcount__ == 1, '8: w_my_box().__grefcount__ == 1'
#print 'w_my_box().__dict__ =', w_my_box().__dict__
#assert hasattr(w_my_box(), 'ellipse'), '9: hasattr(w_my_box(), \'ellipse\')'

my_box2 = MyBox2()
canvas.root.add(my_box2)
my_box2.move(100,100)
del my_box2

gc.collect()

#dia.dia_canvas_item_create (MyBox, parent=canvas.root)

canvas.update_now()
canvas.set_property ('allow_undo', 1)

canvas.set_property ('static_extents', 1)

ext = canvas.get_property ('extents')

ext = (-100.0, -100, 200, 200)
canvas.set_property ('extents', ext)

ext = canvas.get_property ('extents')

view = dia.CanvasView (canvas=canvas, aa=1)

#tool = dia.StackTool ()
tool = PlacementTool (dia.CanvasLine)
view.set_tool (tool)
del tool

#tool = dia.PlacementTool (dia.CanvasLine)
#view.set_tool (tool)
#tool.signal_id = tool.connect ('button_press_event', unset_tool, view)
view.set_tool (None)

display_canvas_view(view)

#tool.push (tool2)
#tool.pop ()
print 'Going into main()...'
gtk.main()

gc.collect()
