import diacanvas
# A custom widget, testing callback inheritance
class MyBox(dia.CanvasBox):

    def __init__(self):
        self.__gobject_init__() # default constructor using our new GType
        #We add an ellipse *shape* to our new Box.
        self.ellipse = dia.shape.Ellipse()
        #position the ellipse in the box
        self.ellipse.ellipse (center=(20,20), width=20, height=20)
        self.ellipse.set_line_width (1)
        
        #Text Schenanigans
        #def text_changed(text_item, shape, text, me):
        #print text_item, shape, text, me
        #self.text = dia.CanvasText() #MyText()
        #self.text.set_child_of(self) # do child -> parent mapping
        #self.text.connect('text_changed', text_changed, self)
        #font = pango.FontDescription('sans 20')
        #self.text.set(text='hello', font=font, width=self.width - 20, height=40)
        #print 'Added,\tself =', self
        #print '\tself.text.parent =', self.text.parent
        #print '\tself.text.canvas =', self.text.canvas
        #self.text.move(10, 30)
        #print 'done'
    
    def do_update (self,  affine):
        print 'do_update(' + str(self) + ', ' + str(affine) + ')'
        #print 'affine.__dict__ = ' + str(affine.__dict__)
	      dia.CanvasBox.on_update (self, affine)
	self.ellipse.request_update() # request update, due to rotation
	           #self.update_child(self.text, affine)

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
	    
