import goocanvas
import gtk

import logging
import conduit
import conduit.DataProvider as DataProvider

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
        #unfortunately we need to keep track of the current canvas 
        #position of all canvas items from this one
        self.positions = {}
        
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
        dw = new_w - self.positions[self.bounding_box]["w"]
        for d in self.datasinks:
            d.get_widget().translate(dw,0)             
        #now update the box width
        self.positions[self.bounding_box]["w"] = new_w
        self.bounding_box.set_property("width",
                                self.positions[self.bounding_box]["w"])
        
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
        padding = Conduit.SIDE_PADDING
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
                y_pos = y + (Conduit.CONDUIT_HEIGHT/2) - (w_h/2)
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
                    + (len(self.datasinks)*Conduit.CONDUIT_HEIGHT) \
                    - (Conduit.CONDUIT_HEIGHT/2) \
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
            #increase to fit added dataprovider
            self.positions[self.bounding_box]["h"] += Conduit.CONDUIT_HEIGHT
            #print "old h = ", self.bounding_box.get_property("height")
            #print "new h = ", self.positions[self.bounding_box]["h"]
            self.bounding_box.set_property("height",
                                self.positions[self.bounding_box]["h"])
        return True
        
    def on_mouse_enter(self, view, target, event):
        print "cond enter"
        self.mouse_inside_me = True
        pass
    
    def on_mouse_leave(self, view, target, event):
        print "cond leave"
        self.mouse_inside_me = False            
        pass
        
       
