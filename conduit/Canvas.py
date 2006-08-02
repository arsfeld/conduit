"""
Manages adding, removing, resizing and drawing the canvas

The Canvas is the main area in Conduit, the area to which DataProviders are 
dragged onto.

Copyright: John Stowers, 2006
License: GPLv2
"""

import goocanvas
import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Conduit as Conduit

class Canvas(goocanvas.CanvasView):
    """
    This class manages many L{conduit.Conduit.Conduit} objects
    """
    
    INITIAL_WIDTH = 600
    INITIAL_HEIGHT = 450
    CANVAS_WIDTH = 450
    CANVAS_HEIGHT = 600

    def __init__(self):
        """
        Draws an empty canvas of the appropriate size
        """
        goocanvas.CanvasView.__init__(self)
        self.set_size_request(Canvas.INITIAL_WIDTH, Canvas.INITIAL_HEIGHT)
        self.set_bounds(0, 0, Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        self.show()
        
        #set up the model 
        self.model = goocanvas.CanvasModelSimple()
        self.root = self.model.get_root_item()
        self.set_model(self.model)

        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        DataProvider.DataProviderTreeView.DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.on_drag_motion)
        
        #set callback to catch new element creation so we can set events
        self.connect("item_view_created", self.on_item_view_created)
        
        self.typeConverter = None        
        #keeps a reference to the currently selected (most recently clicked)
        #canvas item
        self.selected_dataprovider_wrapper = None
        self.selected_conduit = None
        
        #used as a store of connections. Order is important because when
        #a conduit is resized all those below it must be translated down
        #The one at the start of the list should be at the top of the 
        #canvas and so on
        self.conduits = []
        
        #save so that the appropriate signals can be connected and so that
        #other parts of the program can get a ref to the clicked item
        self.newelement = None
        self.newconduit = None
        
    def set_type_converter(self, typeConverter):
        """
        Saves the typeconver as it is needed to determine whether a syncronisation
        is possible
        """
        self.typeConverter = typeConverter
        
    def get_sync_set(self):
        """
        Returns the conduits to be synchronized
        @todo: Should there be any processing in this function???
        
        @returns: A list of conduits to synchronize
        @rtype: C{Conduit[]}
        """        
        return self.conduits
        
    def remove_conduit_overlap(self):
        """
        Searches the cavas from top to bottom to detect if any conduits
        overlap (visually).
        
        This is required (for example) after a conduit above another conduit is
        resized due to another sink being inserted
        """
        for i in range(0, len(self.conduits)):
            c = self.conduits[i]
            try:
                #get the conduit below the current one
                n_c = self.conduits[i+1]
            except:
                #break cause on last one
                break
            x,y,w,h = c.get_conduit_dimensions()
            n_x, n_y, n_w, n_h = n_c.get_conduit_dimensions()
            #check if the current conduit overlaps onto the conduit below it
            if n_y < (y + h):
                new_y = y + h
                #translate only in y direction
                n_c.move_conduit_to(n_x, new_y)
            #x translate not needed/supported
            #if n_x < (x + w):
            #    new_x = x + w
            #    #translate only in y direction
            #    n_c.move_conduit_to(new_x, n_y)
            
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
            y = y + c.get_conduit_height()
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
            if y in range(curr_offset, curr_offset + c.get_conduit_height()):
                return c
            curr_offset = curr_offset + c.get_conduit_height()
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
    
    def on_dataprovider_button_press(self, view, target, event, user_data_dataprovider_wrapper):
        """
        Handle button clicks
        
        @param user_data: The canvas popup item
        @type user_data: L{conduit.Module.ModuleWrapper}
        """
        
        if event.type == gtk.gdk.BUTTON_PRESS:
            #tell the canvas we recieved the click (needed for cut, 
            #copy, past, configure operations
            self.selected_dataprovider_wrapper = user_data_dataprovider_wrapper
            if event.button == 1:
                #TODO: Support dragging canvas items???
                return True
            elif event.button == 3:
                #Only show the menu if the dataprovider isnt already
                #busy being sync'd
                if not self.selected_dataprovider_wrapper.module.is_busy():
                    self.item_popup.popup(
                                                None, None, 
                                                None, event.button, event.time
                                                )
                return True
                
            #TODO: double click to pop up element parameters window
            
    def on_conduit_button_press(self, view, target, event, user_data_conduit):
        """
        Handle button clicks
        """
        
        if event.type == gtk.gdk.BUTTON_PRESS:
            #tell the canvas we recieved the click (needed for cut, 
            #copy, past, configure operations
            self.selected_conduit = user_data_conduit
            if event.button == 1:
                #TODO: Support dragging canvas items???
                return True
            elif event.button == 3:
                if not self.selected_conduit.is_busy():            
                    self.popup.popup(
                                                None, None, 
                                                None, event.button, event.time
                                                )
                return True
                
            #TODO: double click to pop up element parameters window
            
    def resize_canvas(self, new_w, new_h):
        """
        Resizes the canvas
        """
        for c in self.conduits:
            c.resize_conduit_width(new_w)
    
    def add_dataprovider_to_canvas(self, module, x, y):
        """
        Adds a new dataprovider to the Canvas
        
        @param module: The dataprovider wrapper to add to the canvas
        @type module: L{conduit.Module.ModuleWrapper}
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
            existing_conduit.add_dataprovider_to_conduit(module)
            #if we added a new datasource to an existing conduit then it
            #may have been resized. In that case all of the conduits below
            #it may need to be translated
            self.remove_conduit_overlap()
            #Update to connectors to see if they are valid
            #FIXME: This function probbably belongs in the conduit class
            if self.typeConverter is not None:
                existing_conduit.update_connectors_connectedness(self.typeConverter)
        else:
            #create the new conduit
            c = Conduit.Conduit(offset,c_w)
            #add the dataprovider to the conduit
            c.add_dataprovider_to_conduit(module)
            #save so that the appropriate signals can be connected
            self.newconduit = c
            #now add to root element
            self.root.add_child(c)
            self.conduits.append(c)
         
    def remove_dataprovider_from_canvas(self, module):
        """
        Removes a module from the canvas
        
        @param module: The module to remove from the canvas
        @type module: L{conduit.Module.ModuleWrapper}
        """
        if self.selected_dataprovider_wrapper is not None:
            logging.info("Removing module %s" % module)
            
    def update_conduit_connectedness(self):
        """
        Updates all the conduits connectedness based on the conversion
        capabilities of typeConverter
        """
        if self.typeConverter is not None:
            for conduit in self.conduits:
                conduit.update_connector_connectedness(self.typeConverter)

    def on_item_view_created(self, view, itemview, item):
        """
        on_item_view_created
        """
        if isinstance(item, goocanvas.Group):
            if item.get_data("is_a_dataprovider") == True:
                itemview.connect("button_press_event",  self.on_dataprovider_button_press, self.newelement)
            elif item.get_data("is_a_conduit") == True:
                itemview.connect("button_press_event",  self.on_conduit_button_press, self.newconduit)

