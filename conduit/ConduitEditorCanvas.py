import goocanvas
import gtk

import conduit
import conduit.ModuleManager as ModuleManager
import conduit.DataProvider as DataProvider

class ConduitEditorCanvas(goocanvas.CanvasView):
    """
    This class visually describes the state of the main GST pipeline of a
    GstEditor object.  
    """
    
    def __init__(self):
        "Create a new GstEditorCanvas."
        goocanvas.CanvasView.__init__(self)
        self.set_size_request(600, 450)
        self.set_bounds(0, 0, 600, 450)
        self.show()
        
        #set up the model 
        self.model = goocanvas.CanvasModelSimple()
        self.root = self.model.get_root_item()
        self.set_model(self.model)

        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        ModuleManager.DataProviderTreeView.DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.on_drag_motion)
        
        #set callback to catch new element creation so we can set events
        self.connect("item_view_created", self.on_Item_view_created)
        
        
        #keeps a reference to the currently selected (most recently clicked)
        #canvas item
        self.selected_dataprovider = None
        
        #used as a store of connections
        self.conduits = []
        
        #save so that the appropriate signals can be connected
        self.newelement = None
        self.newconduit = None
        
    
    def get_canvas_size(self):
        """
        Returns the size of the canvas in screen units
        
        @todo: There must be a built in way to do this
        @rtype: C{int}, C{int}
        @returns: width, height
        """
        rect = self.get_allocation()
        w = rect.width
        h = rect.height
        return w,h
        
    def get_bottom_of_conduits_coord(self):
        """
        Gets the Y coordinate at the bottom of all visible conduits
        
        @returns: A coordinate (postivive down) from the canvas origin
        @rtype: C{int}
        """
        y = 0
        for c in self.conduits:
            y = y + c.height
        return y
        
    def get_conduit_at_coordinate(self, y):
        """
        Searches through the array of conduits for the one at the
        specified y location.
        
        @param y: The y (positive down) coordinate under which to look for
        a conduit.
        @type y: C{int}
        @returns: a Conduit or None
        @rtype: FIXME
        """
        curr_offset = 0
        for c in self.conduits:
            if y in range(curr_offset, curr_offset + c.height):
                return c
            curr_offset = curr_offset + c.height
        return None                
        
    def on_drag_motion(self, wid, context, x, y, time):
        """
        on_drag_motion
        """
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def set_popup_menus(self, canvas_popup, item_popup):
        """
        setPopup
        """
        self.popup = canvas_popup
        self.item_popup = item_popup
    
    def on_dataprovider_button_press(self, view, target, event, user_data_dataprovider):
        """
        Handle button clicks
        
        @param user_data: The canvas popup item
        @type user_data: L{conduit.ConduitEditorCanvas.ConduitEditorCanvas}
        """
        
        if event.type == gtk.gdk.BUTTON_PRESS:
            #tell the canvas we recieved the click (needed for cut, 
            #copy, past, configure operations
            self.selected_dataprovider = user_data_dataprovider
            if event.button == 1:
                #TODO: Support dragging canvas items???
                return True
            elif event.button == 3:
                self.item_popup.popup(
                                            None, None, 
                                            None, event.button, event.time
                                            )
                return True
                
            #TODO: double click to pop up element parameters window
            
    def on_conduit_button_press(self, view, target, event, user_data_conduit):
        """
        Handle button clicks
        
        @param user_data: The canvas popup item
        @type user_data: L{conduit.ConduitEditorCanvas.ConduitEditorCanvas}
        """
        
        if event.type == gtk.gdk.BUTTON_PRESS:
            #tell the canvas we recieved the click (needed for cut, 
            #copy, past, configure operations
            if event.button == 1:
                #TODO: Support dragging canvas items???
                return True
            elif event.button == 3:
                self.popup.popup(
                                            None, None, 
                                            None, event.button, event.time
                                            )
                return True
                
            #TODO: double click to pop up element parameters window
    
    def add_module_to_canvas(self, module, x, y):
        """
        Adds a new Module to the Canvas
        
        @param module: The module to add to the canvas
        @type module: L{conduit.DataProvider.DataProviderModel}
        @param x: The x location on the canvas to place the module widget
        @type x: C{int}
        @param y: The y location on the canvas to place the module widget
        @type y: C{int}
        """
        
        #save so that the appropriate signals can be connected
        self.newelement = module
        
        #determine the vertical location of the conduit to be created
        offset = self.get_bottom_of_conduits_coord()
        c_w, c_h = self.get_canvas_size()

        #check to see if the dataprovider was dropped on an existin conduit
        #or whether a new one shoud be created
        existing_conduit = self.get_conduit_at_coordinate(y)
        if existing_conduit is not None:
            print "ADDING EXISTING"
            existing_conduit.add_dataprovider_to_conduit(module)
        else:
            #create the new conduit
            c = ConduitEditorCanvas.Conduit(offset,c_w)
            
            #add the dataprovider to the conduit
            if c.add_dataprovider_to_conduit(module) == True:
                #save so that the appropriate signals can be connected
                self.newconduit = c
                #now add to root element
                self.root.add_child(c)
                self.conduits.append(c)
            else:
                "BAD"
         
    def remove_module_from_canvas(self, module):
        """
        Removes a module from the canvas
        
        @param module: The module to remove from the canvas
        @type module: L{conduit.DataProvider.DataProviderModel}
        """
        
        if self.selected_dataprovider is not None:
            print "removing module ", module
            
        #if module.is_connected_to_another()
        #   self._delete_module_connectors
        #self._delete_module
            
    def on_Item_view_created(self, view, itemview, item):
        """
        on_Item_view_created
        """
        if isinstance(item, goocanvas.Group):
            if item.get_data("is_a_dataprovider") == True:
                itemview.connect("button_press_event",  self.on_dataprovider_button_press, self.newelement.module)
            elif item.get_data("is_a_conduit") == True:
                itemview.connect("button_press_event",  self.on_conduit_button_press, self.newconduit)
            
    class Conduit(goocanvas.Group):
        CONDUIT_HEIGHT = 100
        SIDE_PADDING = 10
        def __init__(self, y_from_origin, canvas_width):
            goocanvas.Group.__init__(self)
            #a conduit can hold one datasource and many datasinks
            self.datasource = None
            self.datasinks = []
            #We need some way to tell the canvas that we are a conduit
            self.set_data("is_a_conduit",True)
            #Because the height of a conduit can change depending on how many
            #sinks are in it we must keep track our own height
            self.height = ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT
            #unfortunately we need to keep track of the current canvas 
            #position of all canvas items from this one
            self.positions = {}
            
            #draw a box which will contain the dataproviders
            self.bounding_box = goocanvas.Rect(   
                                    x=0, 
                                    y=y_from_origin, 
                                    width=canvas_width, 
                                    height=ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT,
                                    line_width=3, 
                                    stroke_color="black",
                                    fill_color_rgba=int("eeeeecff",16), 
                                    radius_y=5, 
                                    radius_x=5
                                    )
            self.add_child(self.bounding_box)
            #and store the positions
            self.positions[self.bounding_box] =     {   
                                                    "x" : 0, 
                                                    "y" : y_from_origin,
                                                    "w" : canvas_width,
                                                    "h" : ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT
                                                    }
                        
            
        def move_conduit_to(self,new_x,new_y):
            #because Conduit is a goocanvas.Group all its children get
            #automatically
            dx = new_x - self.positions[self.bounding_box]["x"]
            dy = new_y - self.positions[self.bounding_box]["y"]
            self.translate(dx,dy)
            #so we need to update all children
            for p in self.positions.keys():
                self.positions[p]["x"] += dx
                self.positions[p]["y"] += dx
            
        def move_dataprovider_to(self,dataprovider,new_x,new_y):
            #compute translation amount
            dx = new_x - self.positions[dataprovider]["x"]
            dy = new_y - self.positions[dataprovider]["y"]
            print "Need to translate by dx, dy", dx, dy
            dataprovider.get_widget().translate(dx,dy)
            #update stored position
            self.positions[dataprovider]["x"] = new_x
            self.positions[dataprovider]["y"] = new_y
            
        def add_dataprovider_to_conduit(self, dataprovider_wrapper):
            """
            Adds a dataprovider to the canvas. Positions it appropriately
            so that sources are on the left, and sinks on the right
            
            @returns: True for success
            @rtype: C{bool}
            """
            #determine our width, height, location
            x = self.positions[self.bounding_box]["x"]
            y = self.positions[self.bounding_box]["y"]
            w = self.positions[self.bounding_box]["w"]
            h = self.positions[self.bounding_box]["h"]
            padding = ConduitEditorCanvas.Conduit.SIDE_PADDING
            #now get widget dimensions
            dataprovider = dataprovider_wrapper.module
            w_w, w_h = dataprovider.get_widget_dimensions()
            #if we are adding a new source we may need to resize the box
            resize_box = False
            
            if dataprovider_wrapper.module_type == "source":
                #only one source is allowed
                if self.datasource is not None:
                    print "datasource alreasy present"
                    return False
                else:
                    self.datasource = dataprovider_wrapper.module
                    #new sources go in top left of conduit
                    x_pos = padding
                    y_pos = y + (ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT/2) - (w_h/2)
            elif dataprovider_wrapper.module_type == "sink":
                #only one sink of each kind is allowed
                if dataprovider_wrapper.module in self.datasinks:
                    print "datasink already present"
                    return False
                else:
                    self.datasinks.append(dataprovider_wrapper.module)
                    #new sinks get added at the bottom
                    x_pos = w - padding - w_w
                    y_pos = y \
                        + (len(self.datasinks)*ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT) \
                        - (ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT/2) \
                        - (w_h/2)
                    #check if we also need to resize the bounding box
                    if len(self.datasinks) > 1:
                        resize_box = True
            else:
                    return False
            
            #now store the widget size and add to the conduit 
            new_widget = dataprovider.get_widget()
            self.positions[dataprovider] =  {
                                            "x" : 0,
                                            "y" : 0,
                                            "w" : w_w,
                                            "h" : w_h
                                            }
            #move the widget to its new position
            self.move_dataprovider_to(dataprovider,x_pos,y_pos)
            #add to this group
            self.add_child(new_widget)
            if resize_box is True:
                b_h = self.positions[self.bounding_box]["h"] + ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT
                print "old h = ", self.bounding_box.get_property("height")
                print "new h = ", b_h
                self.bounding_box.set_property("height",b_h)
                self.height = b_h            
            return True
            
        def on_mouse_enter(self, view, target, event):
            print "cond enter"
            self.mouse_inside_me = True
            pass
        
        def on_mouse_leave(self, view, target, event):
            print "cond leave"
            self.mouse_inside_me = False            
            pass
            
       
