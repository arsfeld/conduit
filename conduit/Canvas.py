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

from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
from conduit.Conduit import Conduit
from conduit.Tree import DND_TARGETS
from conduit.ModuleWrapper import ModuleWrapper


class Canvas(goocanvas.Canvas):
    """
    This class manages many L{conduit.Conduit.Conduit} objects
    """
    
    INITIAL_WIDTH = 600
    INITIAL_HEIGHT = 450
    CANVAS_WIDTH = 450
    CANVAS_HEIGHT = 600
    WELCOME_MESSAGE = _("Drag a Dataprovider here to continue")

    def __init__(self):
        """
        Draws an empty canvas of the appropriate size
        """
        goocanvas.Canvas.__init__(self)
        self.set_size_request(Canvas.INITIAL_WIDTH, Canvas.INITIAL_HEIGHT)
        self.set_bounds(0, 0, Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        self.show()
        
        #set up the model 
        self.root = goocanvas.GroupModel()
        self.set_root_item_model(self.root)

        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.on_drag_motion)
        
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
        
        #Show a friendly welcome message on the canvas the first time the
        #application is launched
        self.welcomeMessage = None

        #Keep a list of dataproviders that could not be added because they
        #were unavailable, and should instead be added when they become
        #available (via callback)
        self.pendingDataprovidersToAdd = {}

    def _connect_dataprovider_signals(self, dataproviderWrapper):
        view = self.get_item(dataproviderWrapper.module)
        view.connect("button-press-event",  self.on_dataprovider_button_press, dataproviderWrapper)

    def _connect_conduit_signals(self, conduit):
        view = self.get_item(conduit)
        view.connect("button-press-event",  self.on_conduit_button_press, conduit)

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
        
    def remove_conduit_overlap(self, conduit=None):
        """
        Searches the cavas from top to bottom to detect if any conduits
        overlap (visually).
        
        This is required (for example) after a conduit above another conduit is
        resized due to another sink being inserted
        """
        for i in range(0, len(self.conduits)):
            c = self.conduits[i]
            x,y,w,h = c.get_conduit_dimensions()
            #Special case where the top conduit has been deleted and the new top
            #conduit must be moved up
            if (i == 0) and (y != 0):
                c.move_conduit_by(0, -y)
            else:
                try:
                    #get the conduit below the current one
                    #n_c = next conduit
                    n_c = self.conduits[i+1]
                except:
                    #break cause on last one
                    break
                n_x, n_y, n_w, n_h = n_c.get_conduit_dimensions()
                #check if the current conduit overlaps onto the conduit below it
                diff = (y + h) - n_y 
                #logd("C(y,h) = %s,%s\tNC(y,h) = %s,%s\t Diff = %s" % (y,h,n_y,n_h,diff))
                n_c.move_conduit_by(0, diff)
            
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
            if int(y) in range(int(curr_offset),int(curr_offset + c.get_conduit_height())):
                return c
            curr_offset = curr_offset + c.get_conduit_height()
        return None                
        
    def on_drag_motion(self, wid, context, x, y, time):
        """
        on_drag_motion
        """
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def set_popup_menus(self, conduitPopupXML, dataproviderPopupXML):
        """
        Sets up the popup menus and their callbacks

        @param conduitPopupXML: The menu which is popped up when the user right
        clicks on a conduit
        @type conduitPopupXML: C{gtk.glade.XML}
        @param dataproviderPopupXML: The menu which is popped up when the user right
        clicks on a dataprovider
        @type dataproviderPopupXML: C{gtk.glade.XML}
        """
        self.conduitMenu = conduitPopupXML.get_widget("ConduitMenu")
        self.dataproviderMenu = dataproviderPopupXML.get_widget("DataProviderMenu")

        self.twoWayMenuItem = conduitPopupXML.get_widget("two_way_sync")
        self.twoWayMenuItem.connect("toggled", self.on_two_way_sync_toggle)

        self.slowSyncMenuItem = conduitPopupXML.get_widget("slow_sync")
        self.slowSyncMenuItem.connect("toggled", self.on_slow_sync_toggle)

    def on_two_way_sync_toggle(self, widget):
        """
        Enables or disables two way sync on dataproviders.
        """
        if widget.get_active():
            self.selected_conduit.enable_two_way_sync()
        else:
            self.selected_conduit.disable_two_way_sync()

    def on_slow_sync_toggle(self, widget):
        """
        Enables or disables slow sync of dataproviders.
        """
        if widget.get_active():
            self.selected_conduit.enable_slow_sync()
        else:
            self.selected_conduit.disable_slow_sync()

    def on_dataprovider_button_press(self, view, target, event, user_data_dataprovider_wrapper):
        """
        Handle button clicks
        
        @param user_data_dataprovider_wrapper: The dpw that was clicked
        @type user_data_dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.selected_dataprovider_wrapper = user_data_dataprovider_wrapper
            if event.button == 1:
                return True
            elif event.button == 3:
                #Dont show menu if the dp is just a placeholder
                if self.selected_dataprovider_wrapper.enabled == False:
                    return True
                #Dont show the menu if the dp is bust
                elif self.selected_dataprovider_wrapper.module.is_busy():
                    return True
                else:
                    self.dataproviderMenu.popup(
                                                None, None, 
                                                None, event.button, event.time
                                                )
                    return True
                
            
    def on_conduit_button_press(self, view, target, event, user_data_conduit):
        """
        Handle button clicks on conduits
        """
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.selected_conduit = user_data_conduit
            if event.button == 1:
                return True
            elif event.button == 3:
                #Preset the two way menu items sensitivity
                if not self.selected_conduit.can_do_two_way_sync():
                    self.twoWayMenuItem.set_property("sensitive", False)
                else:
                    self.twoWayMenuItem.set_property("sensitive", True)
                #Set item ticked if two way sync enabled
                self.twoWayMenuItem.set_active(self.selected_conduit.twoWaySyncEnabled)
                #Set item ticked if two way sync enabled
                self.slowSyncMenuItem.set_active(self.selected_conduit.slowSyncEnabled)
                #Show the menu                
                if not self.selected_conduit.is_busy():
                    self.conduitMenu.popup(
                                                None, None, 
                                                None, event.button, event.time
                                                )
                return True
                
            
    def resize_canvas(self, new_w, new_h):
        """
        Resizes the canvas
        """
        for c in self.conduits:
            c.resize_conduit_width(new_w)

    def check_pending_dataproviders(self, wrapper):
        """
        When a dataprovider is added, replace any active instances 
        of PendingDataProvider for that type with a real DataProvider

        @param wrapper: The dataprovider wrapper to insert on canvas in 
        place of a Pending DP
        @type wrapper: L{conduit.Module.ModuleWrapper}
        """
        key = wrapper.get_key()
        if key in self.pendingDataprovidersToAdd:
            logd("SWAPPING OUT")
            for c in self.conduits:
                pending = self.pendingDataprovidersToAdd[key]
                if c.has_dataprovider(pending):
                    #delete old one
                    c.delete_dataprovider_from_conduit(pending)
                    #add new one
                    c.add_dataprovider_to_conduit(wrapper)
                    self._connect_dataprovider_signals(wrapper)
            del self.pendingDataprovidersToAdd[key]

    def make_pending_dataproviders(self, wrapper):
        """
        When a dataprovider is removed, replace any active instances 
        with a PendingDataProvider

        @param wrapper: The dataprovider wrapper to replace with a Pending DP
        @type wrapper: L{conduit.Module.ModuleWrapper} 
        """
        log("Replacing all instances of %s with a PendingDataProvider" % wrapper.get_key())
        for c in self.conduits:
            for dp in c.get_dataproviders_by_key(wrapper.get_key()):
                logd("Found matching dp (%s), make pending!" % dp)

                c.delete_dataprovider_from_conduit(dp)

                pendingWrapper = PendingDataproviderWrapper(wrapper.get_key())
                self.pendingDataprovidersToAdd[wrapper.get_key()] = pendingWrapper
                c.add_dataprovider_to_conduit(pendingWrapper)

    def add_dataprovider_to_canvas(self, key, dataproviderWrapper, x, y):
        """
        Adds a new dataprovider to the Canvas
        
        @param module: The dataprovider wrapper to add to the canvas
        @type module: L{conduit.Module.ModuleWrapper}. If this is None then
        a placeholder should be added (which will get replaced later if/when
        the actual dataprovider becomes available. 
        See self.pendingDataprovidersToAdd
        @param x: The x location on the canvas to place the module widget
        @type x: C{int}
        @param y: The y location on the canvas to place the module widget
        @type y: C{int}
        @returns: The conduit that the dataprovider was added to
        """
        #If module is None we instead add a placeholder dataprovider and
        #add the proper DP when it becomes available via callback
        if dataproviderWrapper == None:
            log("Dataprovider %s unavailable. Adding pending its availability" % key)
            dataproviderWrapper = PendingDataproviderWrapper(key)
            #Store the pending element so it can be removed later            
            self.pendingDataprovidersToAdd[key] = dataproviderWrapper

        #delete the welcome message
        self.delete_welcome_message()
        
        #determine the vertical location of the conduit to be created
        offset = self.get_bottom_of_conduits_coord()
        c_w, c_h = self.get_canvas_size()

        #check to see if the dataprovider was dropped on an existin conduit
        #or whether a new one shoud be created
        c = self.get_conduit_at_coordinate(y)
        if c is not None:
            c.add_dataprovider_to_conduit(dataproviderWrapper)
            #Update to connectors to see if they are valid
            if self.typeConverter is not None:
                c.update_connectors_connectedness(self.typeConverter)
        else:
            #create the new conduit
            c = Conduit(offset,c_w)
            #connect to the conduit resized signal which signals us to 
            #check and remove graphical overlap
            c.connect("conduit-resized", self.remove_conduit_overlap)
            #add the dataprovider to the conduit
            c.add_dataprovider_to_conduit(dataproviderWrapper)
            #save so that the appropriate signals can be connected
            #self.newconduit = c
            #now add to root element
            self.root.add_child(c, -1)
            #connect signals
            self._connect_conduit_signals(c)
            self.conduits.append(c)

        #connect signals
        self._connect_dataprovider_signals(dataproviderWrapper)

        return c
            
    def update_conduit_connectedness(self):
        """
        Updates all the conduits connectedness based on the conversion
        capabilities of typeConverter
        """
        if self.typeConverter is not None:
            for conduit in self.conduits:
                conduit.update_connector_connectedness(self.typeConverter)
                
    def delete_conduit(self, conduit):
        """
        Deletes a conduit and all dataproviders contained within from
        the canvas
        """
        #delete all the datasinks from the conduit
        for s in conduit.datasinks + [conduit.datasource]:
            if s is not None:
                conduit.delete_dataprovider_from_conduit(s)
        #now delete the conduit
        self.root.remove_child(self.root.find_child(conduit))
        i = self.conduits.index(conduit)
        del(self.conduits[i])
        #Now restack the conduits
        self.remove_conduit_overlap()
        #Add the welcome message if we have deleted the last conduit
        self.add_welcome_message()
        
    def add_welcome_message(self):
        """
        Adds a friendly welcome message to the canvas.
        
        Does so only if there are no conduits, otherwise it would just
        get in the way.
        """
        if self.welcomeMessage is None and len(self.conduits) == 0:
            import pango
            self.welcomeMessage = goocanvas.TextModel(  
                                    x=Canvas.CANVAS_WIDTH/2, 
                                    y=Canvas.CANVAS_HEIGHT/3, 
                                    width=2*Canvas.CANVAS_WIDTH/5, 
                                    text=Canvas.WELCOME_MESSAGE, 
                                    anchor=gtk.ANCHOR_CENTER,
                                    alignment=pango.ALIGN_CENTER,
                                    font="Sans 10",
                                    fill_color="black",
                                    )
            self.root.add_child(self.welcomeMessage,-1)   
            del pango

    def delete_welcome_message(self):
        """
        Removes the welcome message from the canvas if it has previously
        been added
        """
        if self.welcomeMessage is not None:
            self.root.remove_child(self.root.find_child(self.welcomeMessage))
            del(self.welcomeMessage)
            self.welcomeMessage = None
            
class PendingDataProvider(goocanvas.GroupModel):
    def __init__(self):
        goocanvas.GroupModel.__init__(self)
        box = goocanvas.RectModel(   
                    x=0, 
                    y=0, 
                    width=DataProvider.WIDGET_WIDTH, 
                    height=DataProvider.WIDGET_HEIGHT,
                    line_width=DataProvider.LINE_WIDTH, 
                    stroke_color="black",
                    fill_color_rgba=DataProvider.TANGO_COLOR_ALUMINIUM1_LIGHT, 
                    radius_y=DataProvider.RECTANGLE_RADIUS, 
                    radius_x=DataProvider.RECTANGLE_RADIUS
                    )
        self.add_child(box, -1)

    def get_UID(self):
        return ""

    def get_widget_dimensions(self):
        return DataProvider.WIDGET_WIDTH, DataProvider.WIDGET_HEIGHT

    def get_status_text(self):
        return "Pending"

    def is_busy(self):
        return False

    def get_configuration(self):
        return {}

    def get_in_type(self):
        return ""

    def get_out_type(self):
        return ""

    def need_configuration(self, need):
        pass

    def set_configured(self, configured):
        pass

    def is_configured(self):
        return False

    def set_status(self, newStatus):
        pass

    def finish(self):
        pass

class PendingDataproviderWrapper(ModuleWrapper):
    def __init__(self, key):
        ModuleWrapper.__init__(
                    self,
                    "name", 
                    "description",
                    "icon_name", 
                    "twoway",               #twoway so can placehold as source or sink
                    "category", 
                    "in_type",
                    "out_type",
                    key.split(':')[0],
                    (),
                    PendingDataProvider(),
                    False)                  #enabled = False so a sync is not performed
        self.key = key

    def get_key(self):
        return self.key


