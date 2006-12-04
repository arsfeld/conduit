"""
Represents a conduit (The joining of one source to one or more sinks)

Copyright: John Stowers, 2006
License: GPLv2
"""
import os.path
import gtk, gtk.gdk
import goocanvas
import gtk
import gobject

import logging
import conduit
import conduit.DataProvider as DataProvider

class Conduit(goocanvas.Group, gobject.GObject):
    """
    Model of a Conduit, which is a one-to-many bridge of DataSources to
    DataSinks.
    
    @ivar datasource: The DataSource to synchronize from
    @type datasource: L{conduit.Module.ModuleWrapper}
    @ivar datasinks: List of DataSinks to synchronize to
    @type datasinks: L{conduit.Module.ModuleWrapper}[]
    """
    HEIGHT = 100
    SIDE_PADDING = 10
    CONNECTOR_RADIUS = 30
    CONNECTOR_LINE_WIDTH = 5
    CONNECTOR_YOFFSET = 20
    CONNECTOR_TEXT_XPADDING = 5
    CONNECTOR_TEXT_YPADDING = 10
    
    __gsignals__ =  { 
                    "conduit-resized": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }
    
    def __init__(self, y_from_origin=0, canvas_width=0):
        """
        Makes and empty conduit ready to hold one datasource and many
        datasinks
        """
        goocanvas.Group.__init__(self)
        gobject.GObject.__init__(self)
        #a conduit can hold one datasource and many datasinks (wrappers)
        self.datasource = None
        self.datasinks = []
        #We need some way to tell the canvas that we are a conduit
        self.set_data("is_a_conduit",True)
        #unfortunately we need to keep track of the current canvas 
        #position of all canvas items from this one
        self.positions = {}
        #When the box is resized the arrows must be resized differently
        self.connectors = {}
        #To handle displaying the status of the dataproviders. Holds a 
        #bunc of goocanvas.Text elements accessed by dataprovider
        self.dataprovider_status = {}
        
        #draw a box which will contain the dataproviders
        self.bounding_box = goocanvas.Rect(   
                                x=0, 
                                y=y_from_origin, 
                                width=canvas_width, 
                                height=Conduit.HEIGHT,
                                line_width=3, 
                                stroke_color="black",
                                fill_color_rgba=DataProvider.TANGO_COLOR_ALUMINIUM1_LIGHT, 
                                radius_y=5, 
                                radius_x=5
                                )
        self.add_child(self.bounding_box)
        #and store the positions
        self.positions[self.bounding_box] =     {   
                                                "x" : 0, 
                                                "y" : y_from_origin,
                                                "w" : canvas_width,
                                                "h" : Conduit.HEIGHT
                                                }

        self.twoWaySyncEnabled = False
                                                
    def on_status_changed(self, dataprovider):
        """
        Callback that recieves status change notifications from the
        dataproviders and adjusts the status text on the canvas
        accordingly
        """
        self.update_status_text(dataprovider,dataprovider.get_status_text())
    
    def get_conduit_dimensions(self):
        """
        Returns the dimensions AND position of the conduit
        
        @returns: x, y, w, h
        @rtype: C{int}, C{int}, C{int}, C{int}
        """
        x = self.positions[self.bounding_box]["x"]
        y = self.positions[self.bounding_box]["y"]
        w = self.positions[self.bounding_box]["w"]
        h = self.positions[self.bounding_box]["h"]
        return x,y,w,h
    
    def get_conduit_height(self):
        """
        Returns the graphical height of this conduit
        (This is the height of the bounding box)
        
        @returns: Height in pixels
        @rtype: C{int}
        """
        return self.positions[self.bounding_box]["h"]
        
    def resize_conduit_height(self, new_h):
        """
        Resizes the conduit height. Does not do anything fancy with the
        dataproviders inside.
        """
        self.positions[self.bounding_box]["h"] = new_h
        self.bounding_box.set_property("height",new_h)
        #This signal tells the canvas to resize us
        self.emit ("conduit-resized")
        
    def resize_conduit_width(self, new_w):
        """
        Resizes the conduit width by
        resizing the bounding box and by translating all the 
        datasinks to the right
        """
        #Translate by
        dw = new_w - self.positions[self.bounding_box]["w"]
        #Only move the datasinks. The datasource stays on the left
        for d in self.datasinks:
            #Translate the widget
            d.module.translate(dw,0)
            #Move the widgets status text
            self.dataprovider_status[d.module].translate(dw,0)
            
        #now update the box width
        self.positions[self.bounding_box]["w"] = new_w
        self.bounding_box.set_property("width",
                                self.positions[self.bounding_box]["w"])
                                
        #Update the length of the connecting lines
        for c in self.connectors:
            self.connectors[c].resize_connector_width(dw)
            
    def move_conduit_by(self,dx,dy):
        """
        Translates the conduit and its children by the included amount.
        Updates the stored positions
        
        Because Conduit is a goocanvas.Group all its children get
        moved automatically when we move but we still update each childs stored 
        position
        """
        self.translate(dx,dy)
        #so we need to update all children
        for p in self.positions.keys():
            self.positions[p]["x"] += dx
            self.positions[p]["y"] += dy
        
    def move_conduit_to(self,new_x,new_y):
        """
        Translates a conduit to the supplied new 
        co-ordinates and updates its stored position
        
        Used after the window is resized or a conduit above us grows
        in size
        """        
        dx = new_x - self.positions[self.bounding_box]["x"]
        dy = new_y - self.positions[self.bounding_box]["y"]
        self.move_conduit_by(dx,dy)
            
    def move_dataprovider_by(self,dataprovider,dx,dy):
        """
        Translates the supplied dataprovider by the specified amount
        and updates the stored position
        """
        dataprovider.module.translate(dx,dy)
        self.positions[dataprovider]["x"] += dx
        self.positions[dataprovider]["y"] += dy
        
    def move_dataprovider_to(self,dataprovider,new_x,new_y):
        """
        Translates a dataprovider to the new 
        co-ordinates and updates its stored position
        
        Used after the window is resized for example
        """
        #compute translation amount
        dx = new_x - self.positions[dataprovider]["x"]
        dy = new_y - self.positions[dataprovider]["y"]
        #translate
        self.move_dataprovider_by(dataprovider,dx,dy)
        
    def add_dataprovider_to_conduit(self, dataprovider_wrapper):
        """
        Adds a dataprovider to the canvas. Positions it appropriately
        so that sources are on the left, and sinks on the right. Adds
        Status text and connecting lines.
        
        The function performs in the following order
        1) Measure our size, and the module to add's size
        2) Move the new dp to its appropriate position and add to me
        3) Draw connecting lines to the dp
        4) Add status text near the dp
        5) Expand if needed
        
        @param dataprovider_wrapper: The L{conduit.Module.ModuleWrapper} 
        containing a L{conduit.DataProvider.DataProviderBase} to add
        @type dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        #----- STEP ONE ------------------------------------------------------
        #determine our width, height, location
        x = self.positions[self.bounding_box]["x"]
        y = self.positions[self.bounding_box]["y"]
        w = self.positions[self.bounding_box]["w"]
        h = self.positions[self.bounding_box]["h"]
        padding = Conduit.SIDE_PADDING
        #now get widget dimensions
        w_w, w_h = dataprovider_wrapper.module.get_widget_dimensions()
        #if we are adding a new source we may need to resize the box
        resize_box = False
        #is the dataprovider going on the left of the right. This is needed
        #because two way dps can go on either side so we cant rely on module
        #type to position it
        horizontal_position = None        

        if dataprovider_wrapper.module_type == "source":
            #only one source is allowed
            if self.datasource is not None:
                #unles it is two-way, then it can go in the other position
                #providing their are no other sinks
                if dataprovider_wrapper.module.is_two_way() and len(self.datasinks) == 0:
                    logging.debug("Adding two way source into sink position")
                    self.datasinks.append(dataprovider_wrapper)
                    #in this case, despite being a source, the dp goes on the right
                    horizontal_position = "right"
                    #new sinks get added at the bottom                    
                    y_pos = y \
                        + (len(self.datasinks)*Conduit.HEIGHT) \
                        - (Conduit.HEIGHT/2) \
                        - (w_h/2)
                else:         
                    logging.warn("Only one datasource allowed per conduit")
                    return
            else:
                self.datasource = dataprovider_wrapper
                #DataSources go on the left
                horizontal_position = "left"
                #And always at the top
                y_pos = y + (Conduit.HEIGHT/2) - (w_h/2)
        elif dataprovider_wrapper.module_type == "sink":
            #only one sink of each kind is allowed
            if dataprovider_wrapper in self.datasinks:
                logging.warn("This datasink already present in this conduit")
                return
            else:
                #temp reference for drawing the connector line
                self.datasinks.append(dataprovider_wrapper)
                #Datasinks go on the right
                horizontal_position = "right"
                #And always added at the bottom
                y_pos = y \
                    + (len(self.datasinks)*Conduit.HEIGHT) \
                    - (Conduit.HEIGHT/2) \
                    - (w_h/2)
                #check if we also need to resize the bounding box
                if len(self.datasinks) > 1:
                    resize_box = True
        else:
                logging.warn("Only sinks or sources may be added to conduit")
                return

        #Connect to the signal which is fired when dataproviders change
        #their status (initialized, synchronizing, etc
        dataprovider_wrapper.module.connect("status-changed", self.on_status_changed)
        #----- STEP TWO ------------------------------------------------------        
        #now store the widget size and add to the conduit 
        new_widget = dataprovider_wrapper.module
        self.positions[dataprovider_wrapper] =  {
                                        "x" : 0,
                                        "y" : 0,
                                        "w" : w_w,
                                        "h" : w_h
                                        }
        #move the widget to its new position
        if horizontal_position == "left":
            x_pos = padding
        elif horizontal_position == "right":
            x_pos = w - padding - w_w
        else:
            logging.warn("UNKNOWN HORIZONTAL POSITION")

        self.move_dataprovider_to(dataprovider_wrapper,x_pos,y_pos)
        #add to this group
        self.add_child(new_widget)
        
        #----- STEP THREE ----------------------------------------------------                
        #Draw the pretty curvy connector lines only if there
        #is one source and >1 sinks
        if self.datasource != None and len(self.datasinks) > 0:
            #check if there are any sinks which are unconnected and connect them
            for sink in self.datasinks:
                if sink not in self.connectors:
                    #Draw the connecting lines between the dataproviders
                    self.add_connector_to_canvas(self.datasource,sink)

        #----- STEP FOUR -----------------------------------------------------
        #Draw status text
        if horizontal_position == "left":
            x_offset = w_w + Conduit.CONNECTOR_TEXT_XPADDING
            #Source text is above the line
            y_offset = w_h - Conduit.CONNECTOR_YOFFSET - Conduit.CONNECTOR_TEXT_YPADDING
            anchor = gtk.ANCHOR_WEST
        elif horizontal_position == "right":
            x_offset = - Conduit.CONNECTOR_TEXT_XPADDING
            #Sink text is below the line
            y_offset = w_h - Conduit.CONNECTOR_TEXT_YPADDING
            anchor = gtk.ANCHOR_EAST         
        else:
            logging.warn("UNKNOWN HORIZONTAL POSITION")    
        msg = dataprovider_wrapper.module.get_status_text()             
        statusText = self.make_status_text(x_pos+x_offset, y_pos+y_offset, msg)
        statusText.set_property("anchor", anchor)
        self.dataprovider_status[dataprovider_wrapper.module] = statusText
        self.add_child(statusText)            

        #----- STEP FIVE -----------------------------------------------------                
        if resize_box is True:
            #increase to fit added dataprovider
            new_h = self.get_conduit_height() + Conduit.HEIGHT
            self.resize_conduit_height(new_h)

        #----- STEP SIX ------------------------------------------------------
        #Check if a two way sync can still be performed
        if not self.can_do_two_way_sync():
            self.disable_two_way_sync()
            
    def add_connector_to_canvas(self, source, sink):
        """
        Adds nice curved line which indicates a sync relationship to the canvas
        """
        #calculate the start point
        fromX = self.positions[source]["x"] + self.positions[source]["w"]
        fromY = self.positions[source]["y"] + self.positions[source]["h"] - Conduit.CONNECTOR_YOFFSET
        #calculate end point
        toX = self.positions[sink]["x"] #connect to inside side
        toY = self.positions[sink]["y"] + self.positions[sink]["h"] - Conduit.CONNECTOR_YOFFSET
        #draw the connector and add it as child
        con = Connector(fromX, fromY, toX, toY)
        self.add_child(con)
        self.connectors[sink] = con

    def update_connectors_connectedness(self, typeConverter):
        """
        Updates the color of the connectors joining the source to
        the specified sink.
        
        The color of the connector represents whether the synchronisation 
        can be made without conversion, made only via conversion through text, 
        or not made at all (there is no conversion path which exists)
        """
        for sink in self.datasinks:
            #need to check if there is actually a datasource
            if self.datasource is not None:
                if self.datasource.out_type == sink.in_type:
                    self.connectors[sink].set_color("black")
                else:
                    #Conversion through text allowed
                    #FIXME: Dont draw invalid connections here, or draw a dotted line or something
                    if not typeConverter.conversion_exists(self.datasource.out_type, sink.in_type):
                        self.connectors[sink].set_color("red")

        if self.is_two_way():
            self.connectors[self.datasinks[0]].set_two_way(True)
        else:
            for sink in self.datasinks[1:]:
                self.connectors[sink].set_two_way(False)

    def make_status_text(self, x, y, text=""):
        """
        Creates a L{goocanvas.Text} object containing text and at the 
        supplied position
        """
        text = goocanvas.Text   (  
                                x=x, 
                                y=y, 
                                width=80, 
                                text=text, 
                                anchor=gtk.ANCHOR_WEST, 
                                font="Sans 7",
                                fill_color_rgba=DataProvider.TANGO_COLOR_ALUMINIUM2_MID,
                                )
        return text
        
    def update_status_text(self, dataprovider, newText):
        """
        Updates the status text which is displayed adjacent to the conduit 
        which it describes
        """
        self.dataprovider_status[dataprovider].set_property("text",newText)
        
    def is_busy(self):
        """
        Tests if it is currently safe to modify the conduits settings
        or start/restart as synchronisation. 
        
        @returns: True if the conduit is currenlty performing a synchronisation
        operaton on one or more of its contained DataProviders
        @rtype: C{bool}
        """
        for sink in self.datasinks + [self.datasource]:
            if sink is not None:
                if sink.module.is_busy():
                    return True
                
        return False
        
    def has_dataprovider(self, dataprovider):
        """
        Checks if the conduit containes the specified dataprovider
        
        @type dataprovider: L{Conduit.Module.ModuleWrapper}
        @returns: True if the conduit contains the dataprovider
        @rtype: C{bool}
        """
        if dataprovider in self.datasinks + [self.datasource]:
            return True
        else:
            return False
            
    def delete_connector(self, dataprovider):
        """
        Deletes the connector associated with the given dataprovider
        """
        connector = self.connectors[dataprovider]
        self.remove_child(self.find_child(connector))
        del(self.connectors[dataprovider])
    
    def delete_status_text(self, dataprovider):
        """
        Deletes status text from the canvas associated with the given dataprovider
        """
        text = self.dataprovider_status[dataprovider.module]
        self.remove_child(self.find_child(text))
        del(self.dataprovider_status[dataprovider.module])
        
    def delete_dataprovider(self, dataprovider):
        """
        Deletes dataprovider
        """
        #Delete the widget
        child = self.find_child(dataprovider.module)
        self.remove_child(child)
        #Delete its stored position
        del(self.positions[dataprovider])
        #Sources and sinks are stored seperately so must be deleted from different
        #places. Lucky there is only one source or this would be harder....
        if dataprovider == self.datasource:
            del(self.datasource)
            self.datasource = None
        elif dataprovider in self.datasinks:
            i = self.datasinks.index(dataprovider)
            del(self.datasinks[i])
        else:
            logging.warn("Could not remove %s" % dataprovider)
        
    def delete_dataprovider_from_conduit(self, dataprovider):
        """
        Removes the specified conduit from the canvas
        """
        if dataprovider == self.datasource:
            logging.debug("Deleting Source %s" % dataprovider)
            #remove ALL connectors
            for sink in self.datasinks:
                self.delete_connector(sink)
            #remove the status text
            self.delete_status_text(dataprovider)
            #remove the dataprovider widget and instance
            self.delete_dataprovider(dataprovider)
        elif dataprovider in self.datasinks:
            logging.debug("Deleting Sink %s" % dataprovider)  
            #remove the connector
            if self.datasource is not None:
                self.delete_connector(dataprovider)
            #remove the status text
            self.delete_status_text(dataprovider)
           
            i = self.datasinks.index(dataprovider)
            #If we deleted the last sink then we dont need to move sinks below it up
            if (i == (len(self.datasinks)-1)) and (len(self.datasinks) > 1):
                #remove the dataprovider widget and instance
                self.delete_dataprovider(dataprovider)  
                self.resize_conduit_height(self.get_conduit_height() - Conduit.HEIGHT)    
            else:
                #remove the dataprovider widget and instance
                self.delete_dataprovider(dataprovider)  
                #Move the datasinks, and status text below the deleted one 
                #upwards and fix all their connectors
                for j in range(i, len(self.datasinks)):
                    #logging.debug("Del Conduit at Index %s, Checking %s of %s" % (i,j,len(self.datasinks)))
                    #Delete the old connectors
                    if self.datasource is not None:
                        self.delete_connector(self.datasinks[j])
                    #Move the sink up
                    self.move_dataprovider_by(self.datasinks[j], 0,-Conduit.HEIGHT)
                    #Move the status text up
                    self.dataprovider_status[self.datasinks[j].module].translate(0,-Conduit.HEIGHT)
                    #Make a new connector
                    if self.datasource is not None:
                        self.add_connector_to_canvas(self.datasource,self.datasinks[j])

                #Shrink the box (but never shrink it to zero or we cant see anything)
                new_h = self.get_conduit_height() - Conduit.HEIGHT
                if new_h > 0:
                    self.resize_conduit_height(new_h)

        else:
            logging.warn("Could not find dataprovider %s to delete" % dataprovider)

        #Can the conduit can now perform a two way sync if requested by the user?
        if not self.can_do_two_way_sync():
            self.disable_two_way_sync()

    def can_do_two_way_sync(self):
        """
        Checks if the conduit is eleigable for two way sync, which is true
        if it has one source and once sink. Two way doesnt make sense in 
        any other case
        """
        if self.datasource != None and len(self.datasinks) == 1:
            return self.datasource.module.is_two_way() and self.datasinks[0].module.is_two_way()
        return False

    def enable_two_way_sync(self):
        logging.debug("Enabling Two Way Sync")
        self.twoWaySyncEnabled = True
        if self.can_do_two_way_sync():
            self.connectors[self.datasinks[0]].set_two_way(True)
                    
    def disable_two_way_sync(self):
        logging.debug("Disabling Two Way Sync")
        self.twoWaySyncEnabled = False
        if self.can_do_two_way_sync():
            self.connectors[self.datasinks[0]].set_two_way(False)

    def is_two_way(self):
        return self.can_do_two_way_sync() and self.twoWaySyncEnabled

           
class Connector(goocanvas.Group):
    """
    Represents the graphical connection between a datasource and a datasink

    @todo: Extend this to draw end caps on the line to represent two way
    @todo: Animate the connector when synchronizing

    Contains a single goocanvas.Path element
    """

    def __init__(self, fromX, fromY, toX, toY):
        goocanvas.Group.__init__(self)
        self.fromX = fromX
        self.fromY = fromY
        self.toX = toX
        self.toY = toY
        self.twoway = False

        #The path is a goocanvas.Path element. 
        self.path = goocanvas.Path(data="",stroke_color="black",line_width=Conduit.CONNECTOR_LINE_WIDTH)                
        self._draw_path()
        self.add_child(self.path)

        self.left_end_round = goocanvas.Ellipse(
                                    center_x=fromX, 
                                    center_y=fromY, 
                                    radius_x=6, 
                                    radius_y=6, 
                                    fill_color="black", 
                                    line_width=0.0
                                    )
        points = goocanvas.Points([(fromX, fromY), (fromX-1, fromY)])
        self.left_end_arrow = goocanvas.Polyline(
                            points=points,
                            stroke_color="black",
                            line_width=5,
                            end_arrow=True,
                            arrow_tip_length=3,
                            arrow_length=3,
                            arrow_width=3
                            )

        

        points = goocanvas.Points([(toX-1, toY), (toX, toY)])
        self.right_end = goocanvas.Polyline(
                            points=points,
                            stroke_color="black",
                            line_width=5,
                            end_arrow=True,
                            arrow_tip_length=3,
                            arrow_length=3,
                            arrow_width=3
                            )
        self._draw_arrow_ends()

        self.add_child(self.right_end)

    def _draw_arrow_ends(self):
        #Always draw the right arrow end for the correct width
        points = goocanvas.Points([(self.toX-1, self.toY), (self.toX, self.toY)])
        self.right_end.set_property("points",points)
        #selectively add or remove a rounded left or right arrow
        #remove both
        arrowidx = self.find_child(self.left_end_arrow)
        if arrowidx != -1:
            self.remove_child(arrowidx)
        roundidx = self.find_child(self.left_end_round)
        if roundidx != -1:
            self.remove_child(roundidx)
        
        if self.twoway == True:
            self.add_child(self.left_end_arrow)
        else:
            self.add_child(self.left_end_round)

    def _draw_path(self):
        """
        Builds a SVG path statement. This represents the (optionally) curved 
        connector between a datasource and datasink. Then assigns the path
        to the internal path object
        """
        #Dont build curves if its just a dead horizontal link
        if self.fromY == self.toY:
            #draw simple straight line
            p = "M%s,%s "           \
                "L%s,%s "       %   (
                                    self.fromX,self.fromY,  #absolute start point
                                    self.toX,self.toY       #absolute line to point
                                    )
        else:
            #draw pretty curvy line 
            r = Conduit.CONNECTOR_RADIUS  #radius of curve
            ls = 40 #len of start straight line segment
            ld = self.toY - self.fromY - 2*r
            p = "M%s,%s "           \
                "l%s,%s "           \
                "q%s,%s %s,%s "     \
                "l%s,%s "           \
                "q%s,%s %s,%s "     \
                "L%s,%s"        %   (
                                    self.fromX,self.fromY,  #absolute start point
                                    ls,0,                   #relative length line +x
                                    r,0,r,r,                #quarter circle
                                    0,ld,                   #relative length line +y
                                    0,r,r,r,                #quarter circle
                                    self.toX,self.toY       #absolute line to point
                                    )
        #Asign to the internal path object
        self.path.set_property("data",p)
            
    def resize_connector_width(self, dw):
        """
        Adjusts the size of the connector. Used when the window is resized
        
        @param dw: The change in width
        @type dw: C{int}
        """
        #Only the X location changes
        self.toX += dw
        self._draw_path()
        self._draw_arrow_ends()

    def set_color(self, color):
        """
        @param color: The connectors new color
        @type color: C{string}
        """
        self.path.set_property("stroke_color",color)

    def set_two_way(self, twoway):
        """
        @param color: The connectors new color
        @type color: C{string}
        """
        self.twoway = twoway
        self._draw_arrow_ends()

