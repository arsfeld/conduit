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
        self.set_bounds(0, 0, 1000, 1000)
        self.show()
        
        #set up the model 
        self.model = goocanvas.CanvasModelSimple()
        self.root = self.model.get_root_item()
        self.set_model(self.model)

        # create a main pipeline to contain all child elements
        #self.pipeline = gsteditorelement.PipelineModel()
        
        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        ModuleManager.DataProviderTreeView.DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.motion_cb)
        
        #set callback to catch new element creation so we can set events
        self.connect("item_view_created", self.onItemViewCreated)
        
        #set callbacks for background clicks
        self.connect_after("button_press_event", self._onButtonPress)
        
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
        #get widget for the module
        widget = module.get_widget()
        #adjust to DND position (where it was dropped)
        widget_width, widget_height = module.get_widget_dimensions()
        widget.translate(   x-(widget_width/2),
                            y-(widget_height/2)
                            )
        #add to canvas
        self.root.add_child(widget)        
    
    def moveElement(self, element):
        """
        Repositions an element on the canvas and re-draws connectors
        """
        raise NotImplementedError
        
    def deleteElement(self, element):
        """
        Remove an element and any connecting lines from the canvas
        """
        raise NotImplementedError
    
    def deleteConnector(self, connector):
        """
        Deletes a connecting line between a src and a sink
        """
        raise NotImplementedError
    
    def drawNewConnector(self, src, sink):
        """
        Draws a new connector from a src to a sink
        """
        raise NotImplementedError
    
    def onItemViewCreated(self, view, itemview, item):
        """
        onItemViewCreated
        """
        print "element created"
        #this assumes any Group is an element.  this may need to change...
        if item.get_data("item_type") == "pad":
            print "connecting pad signals"
            itemview.connect("enter_notify_event",  self.newelement.onPadEnter)
            itemview.connect("leave_notify_event",  self.newelement.onPadLeave)
            itemview.connect("button_press_event",  self.newelement.onPadPress)
            itemview.connect("button_release_event",self.newelement.onPadRelease)
        if isinstance(item, goocanvas.Group):
            print "connected signal"
            itemview.connect("button_press_event",  self.newelement.onButtonPress, self)
            itemview.connect("motion_notify_event", self.newelement.onMotion)
            itemview.connect("enter_notify_event",  self.newelement.onEnter)
            itemview.connect("leave_notify_event",  self.newelement.onLeave)
