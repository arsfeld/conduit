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
        self.connect('drag-motion', self.motion_cb)
        
        #set callback to catch new element creation so we can set events
        self.connect("item_view_created", self.onItemViewCreated)
        
        #set callbacks for background clicks
        self.connect_after("button_press_event", self._onButtonPress)
        
        #keeps a reference to the currently selected (most recently clicked)
        #canvas item
        self.selcted_dataprovider = None
        
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
        
    def motion_cb(self, wid, context, x, y, time):
        """
        motion_cb
        """
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def set_popup_menus(self, canvas_popup, item_popup):
        """
        setPopup
        """
        self.popup = canvas_popup
        self.item_popup = item_popup
    
    def _onButtonPress(self, view, event):
        """
        onButtonPress
        """
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 3:
                # pop up menu
                self.popup.popup(None, None, None, event.button, event.time)
                return True
    
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
        offset = len(self.conduits) * ConduitEditorCanvas.Conduit.CONDUIT_HEIGHT
        c_w, c_h = self.get_canvas_size()

        #create the conduit
        c = ConduitEditorCanvas.Conduit(offset,c_w)
        
        #add the dataprovider to the conduit
        if c.add_dataprovider_to_conduit(module) == True:
            #save so that the appropriate signals can be connected
            self.newconduit = c
            #now add to root element
            self.root.add_child(c)
            self.conduits.append(c)
         
    def remove_module_from_canvas(self, module):
        """
        Removes a module from the canvas
        
        @param module: The module to remove from the canvas
        @type module: L{conduit.DataProvider.DataProviderModel}
        """
        
        if self.selcted_dataprovider is not None:
            print "removing module ", module
            
        #if module.is_connected_to_another()
        #   self._delete_module_connectors
        #self._delete_module
            
    def link_modules(self, src, sink):
        """
        Links two modules together graphically
        
        @param src: The module to link FROM
        @type src: L{conduit.DataProvider.DataProviderModel}
        @param sink: The module to link TO
        @type sink: L{conduit.DataProvider.DataProviderModel}
        """
        raise NotImplementedError    
    
    def move_module_connectors(self, module):
        """
        Redraws an element's connection to other modules
        
        @param module: The module whose connections are redrawn
        @type module: L{conduit.DataProvider.DataProviderModel}
        """
        raise NotImplementedError
        
    def _delete_module(self, module):
        """
        Remove an element and any connecting lines from the canvas

        @param module: The module whose connections are redrawn
        @type module: L{conduit.DataProvider.DataProviderModel}
        """
        raise NotImplementedError
    
    def _delete_module_connectors(self, module):
        """
        Deletes all connections from the module
        
        @param module: The module whose connections are deleted
        @type module: L{conduit.DataProvider.DataProviderModel}
        """
        raise NotImplementedError
    
    def _draw_new_connector(self, src, sink):
        """
        Draws a new connector from a src to a sink

        @param src: The module draw a connector FROM
        @type src: L{conduit.DataProvider.DataProviderModel}
        @param sink: The module to draw a connector TO
        @type sink: L{conduit.DataProvider.DataProviderModel}
        """
        raise NotImplementedError
    
    def onItemViewCreated(self, view, itemview, item):
        """
        onItemViewCreated
        """
        if isinstance(item, goocanvas.Group):
            print "new conduit = ", self.newconduit
            print "new dp = ", self.newelement.module
            if item.get_data("is_a_dataprovider") == True:
                print "Connecting dataprovider"
                itemview.connect("button_press_event",  self.newelement.module.onButtonPress, self)
                itemview.connect("motion_notify_event", self.newelement.module.onMotion)
                itemview.connect("enter_notify_event",  self.newelement.module.onEnter)
                itemview.connect("leave_notify_event",  self.newelement.module.onLeave)
            elif item.get_data("is_a_conduit") == True:
                print "Connecting conduit"
                itemview.connect("enter_notify_event",  self.newconduit.on_mouse_enter)
                itemview.connect("leave_notify_event",  self.newconduit.on_mouse_leave)
            
    class Conduit(goocanvas.Group):
        CONDUIT_HEIGHT = 100
        SIDE_PADDING = 10
        def __init__(self, y_from_origin, canvas_width):
            goocanvas.Group.__init__(self)
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
            #We need some way to tell the canvas that we are a conduit
            self.set_data("is_a_conduit",True)
            self.mouse_inside_me = False
        
        def add_dataprovider_to_conduit(self, dataprovider_wrapper):
            """
            Adds a dataprovider to the canvas. Positions it appropriately
            so that sources are on the left, and sinks on the right
            
            @returns: True for success
            @rtype: C{bool}
            """
            #only sinks and sources supported
            if dataprovider_wrapper.module_type == "source" or dataprovider_wrapper.module_type == "sink":
                dataprovider = dataprovider_wrapper.module

                #determine our width, height, location
                w = self.bounding_box.get_property("width")
                h = self.bounding_box.get_property("height")
                x = self.bounding_box.get_property("x")
                y = self.bounding_box.get_property("y")

                #get the dataprovider widget and its dimensions
                new_widget = dataprovider.get_widget()
                w_w, w_h = dataprovider.get_widget_dimensions()
                
                #position the widget
                padding = ConduitEditorCanvas.Conduit.SIDE_PADDING
                #determine dp type. Sources get drawn on the left, sinks on right
                if dataprovider_wrapper.module_type == "source":
                    x_pos = padding
                elif dataprovider_wrapper.module_type == "sink":
                    x_pos = w - padding - w_w
                else:
                    return False
                    
                new_widget.translate(   
                                    x_pos,
                                    y + (h/2) - (w_h/2)
                                    )
                
                self.add_child(new_widget)
                return True
            else:
                return False
            
        def on_mouse_enter(self, view, target, event):
            print "cond enter"
            self.mouse_inside_me = True
            pass
        
        def on_mouse_leave(self, view, target, event):
            print "cond leave"
            self.mouse_inside_me = False            
            pass
            
        def repaint_me(self):
            pass
        
