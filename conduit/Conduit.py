"""
Represents a conduit (The joining of one source to one or more sinks)

Copyright: John Stowers, 2006
License: GPLv2
"""
import goocanvas
import gtk

import logging
import conduit
import conduit.DataProvider as DataProvider

class Conduit(goocanvas.Group):
    """
    Model of a Conduit, which is a one-to-many bridge of DataSources to
    DataSinks.
    
    @ivar datasource: The DataSource to synchronize from
    @type datasource: L{conduit.Module.ModuleWrapper}
    @ivar datasinks: List of DataSinks to synchronize to
    @type datasinks: L{conduit.Module.ModuleWrapper}[]
    """
    CONDUIT_HEIGHT = 100
    SIDE_PADDING = 10
    CONNECTOR_PAD_START = 30
    CONNECTOR_PAD_END = 30
    CONNECTOR_RADIUS = 30
    CONNECTOR_LINE_WIDTH = 5
    
    def __init__(self, y_from_origin, canvas_width):
        goocanvas.Group.__init__(self)
        #a conduit can hold one datasource and many datasinks (wrappers)
        self.datasource = None
        self.datasinks = []
        #We need some way to tell the canvas that we are a conduit
        self.set_data("is_a_conduit",True)
        #unfortunately we need to keep track of the current canvas 
        #position of all canvas items from this one
        self.positions = {}
        #When the box is resized the arrows must be resized differently
        self.connectors = []
        #To handle displaying the status of the dataproviders. Holds a 
        #bunc of goocanvas.Text elements accessed by dataprovider
        self.dataprovider_status = {}
        
        #draw a box which will contain the dataproviders
        self.bounding_box = goocanvas.Rect(   
                                x=0, 
                                y=y_from_origin, 
                                width=canvas_width, 
                                height=Conduit.CONDUIT_HEIGHT,
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
                                                "h" : Conduit.CONDUIT_HEIGHT
                                                }
                                                
    def on_status_changed(self, dataprovider, status):
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
            d.module.get_widget().translate(dw,0)
            #Move the widgets status text
            self.dataprovider_status[d.module].translate(dw,0)
            
        #now update the box width
        self.positions[self.bounding_box]["w"] = new_w
        self.bounding_box.set_property("width",
                                self.positions[self.bounding_box]["w"])
                                
        #Update the length of the connecting lines
        for c in self.connectors:
            self.adjust_connector_width(c, dw)
            
        
    def move_conduit_to(self,new_x,new_y):
        #because Conduit is a goocanvas.Group all its children get
        #moved automatically when we move
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
        #translate
        dataprovider.module.get_widget().translate(dx,dy)
        #update stored position
        self.positions[dataprovider]["x"] = new_x
        self.positions[dataprovider]["y"] = new_y
        
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
        
        if dataprovider_wrapper.module_type == "source":
            #only one source is allowed
            if self.datasource is not None:
                logging.warn("Only one datasource allowed per conduit")
                return
            else:
                self.datasource = dataprovider_wrapper
                #New sources go in top left of conduit
                x_pos = padding
                y_pos = y + (Conduit.CONDUIT_HEIGHT/2) - (w_h/2)
        elif dataprovider_wrapper.module_type == "sink":
            #only one sink of each kind is allowed
            if dataprovider_wrapper in self.datasinks:
                logging.warn("This datasink already present in this conduit")
                return
            else:
                #temp reference for drawing the connector line
                self.datasinks.append(dataprovider_wrapper)
                #new sinks get added at the bottom
                x_pos = w - padding - w_w
                y_pos = y \
                    + (len(self.datasinks)*Conduit.CONDUIT_HEIGHT) \
                    - (Conduit.CONDUIT_HEIGHT/2) \
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
        new_widget = dataprovider_wrapper.module.get_widget()
        self.positions[dataprovider_wrapper] =  {
                                        "x" : 0,
                                        "y" : 0,
                                        "w" : w_w,
                                        "h" : w_h
                                        }
        #move the widget to its new position
        self.move_dataprovider_to(dataprovider_wrapper,x_pos,y_pos)
        #add to this group
        self.add_child(new_widget)
        
        #----- STEP THREE ----------------------------------------------------                
        #Draw the pretty curvy connector lines only if there
        #is one source and >1 sinks
        if len(self.datasinks) > 0 and self.datasource != None:
            #calculate the start point
            fromX = self.positions[self.datasource]["x"] + self.positions[self.datasource]["w"]
            fromY = self.positions[self.datasource]["y"] + self.positions[self.datasource]["h"] - 20
            #if we have added a sink then connect to it, otherwise we 
            #have only one sink and we should draw to it
            if len(self.datasinks) == 1:
                sink = self.datasinks[0]
            else:
                sink = dataprovider_wrapper
            
            toX = self.positions[sink]["x"] #inside 
            toY = self.positions[sink]["y"] + self.positions[sink]["h"] - 20
            #Draw the connecting lines between the dataproviders
            self.add_connector_to_canvas(fromX,fromY,toX,toY)                               

        #----- STEP FOUR -----------------------------------------------------                
        if dataprovider_wrapper.module_type == "source":
            x_offset = w_w + 5
            y_offset = w_h - 30
            anchor = gtk.ANCHOR_WEST
        else:
            x_offset = - 5
            y_offset = w_h - 10
            anchor = gtk.ANCHOR_EAST            
        msg = dataprovider_wrapper.module.get_status_text()             
        statusText = self.make_status_text(x_pos+x_offset, y_pos+y_offset, msg)
        statusText.set_property("anchor", anchor)
        self.dataprovider_status[dataprovider_wrapper.module] = statusText
        self.add_child(statusText)            

        #----- STEP FIVE -----------------------------------------------------                
        if resize_box is True:
            #increase to fit added dataprovider
            self.positions[self.bounding_box]["h"] += Conduit.CONDUIT_HEIGHT
            self.bounding_box.set_property("height",
                                self.positions[self.bounding_box]["h"])
            
    def make_connector_svg_string(self, fromX, fromY, toX, toY):
        """
        Builds a SVG path statement string based on its input
        
        @returns: A valid SVG path descriptor
        @rtype: C{string}
        """
        #Dont build curves if its just a dead horizontal link
        if fromY == toY:
            #draw simple straight line
            p = "M%s,%s "           \
                "L%s,%s "       %   (
                                    fromX,fromY,    #absolute start point
                                    toX, toY        #absolute line to point
                                    )
        else:
            #draw pretty curvy line 
            r = 20  #radius of curve
            ls = 40 #len of start straight line segment
            ld = toY - fromY - 2*r
            p = "M%s,%s "           \
                "l%s,%s "           \
                "q%s,%s %s,%s "     \
                "l%s,%s "           \
                "q%s,%s %s,%s "     \
                "L%s,%s"        %   (
                                    fromX,fromY,    #absolute start point
                                    ls,0,           #relative length line +x
                                    r,0,r,r,        #quarter circle
                                    0,ld,           #relative length line +y
                                    0,r,r,r,        #quarter circle
                                    toX, toY        #absolute line to point
                                    )
            #create and return                                    
        return p
               
    def add_connector_to_canvas(self, fromX, fromY, toX, toY, bidirectional=False):
        """
        Adds nice curved line which indicates a sync relationship to the canvas
        """
        #The path is a goocanvas.Path element. 
        svgPathString = self.make_connector_svg_string(fromX, fromY, toX, toY)
        path = goocanvas.Path(data=svgPathString,stroke_color="black",line_width=5)                
        self.add_child(path)
        #Add to list of connectors to allow resize later
        self.positions[path] =  {
                                "x" : fromX,
                                "y" : fromY,
                                "w" : toX - fromX,
                                "h" : toY - fromY
                                }
        self.connectors.append(path)

    def adjust_connector_width(self, connector, dw):
        """
        Adjusts the size of the connector. Used when the window is resized
        
        @param connector: The connector to resize
        @type connector: C{goocanvas.Path}
        @param dw: The change in width
        @type dw: C{int}
        """
        
        #Get the current start and end points of the conector
        #Little bit hacky but we know that
        #toX = w - fromX and toY = h - fromY
        fromX = self.positions[connector]["x"]
        fromY = self.positions[connector]["y"]
        toX = self.positions[connector]["w"] + fromX + dw
        toY = self.positions[connector]["h"] + fromY
        
        #Save new width
        self.positions[connector]["w"] += dw
        #Update path
        svgData = self.make_connector_svg_string(fromX, fromY, toX, toY)
        connector.set_property("data",svgData)

    def make_status_text(self, x, y, text=""):
        text = goocanvas.Text   (  
                                x=x, 
                                y=y, 
                                width=80, 
                                text=text, 
                                anchor=gtk.ANCHOR_WEST, 
                                font="Sans 7",
                                fill_color_rgba=int("555753ff",16),
                                )
        return text
        
    def update_status_text(self, dataprovider, newText):
        self.dataprovider_status[dataprovider].set_property("text",newText)
        
        
        
