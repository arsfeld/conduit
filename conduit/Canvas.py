"""
Manages adding, removing, resizing and drawing the canvas

The Canvas is the main area in Conduit, the area to which DataProviders are 
dragged onto.

Copyright: John Stowers, 2006
License: GPLv2
"""
import gobject
import goocanvas
import gtk
import pango
from gettext import gettext as _

from conduit import log,logd,logw
from conduit.Conduit import Conduit
from conduit.Tree import DND_TARGETS
from conduit.ModuleWrapper import ModuleWrapper

#Tango colors taken from 
#http://tango.freedesktop.org/Tango_Icon_Theme_Guidelines
TANGO_COLOR_BUTTER_LIGHT = int("fce94fff",16)
TANGO_COLOR_BUTTER_MID = int("edd400ff",16)
TANGO_COLOR_BUTTER_DARK = int("c4a000ff",16)
TANGO_COLOR_ORANGE_LIGHT = int("fcaf3eff",16)
TANGO_COLOR_ORANGE_MID = int("f57900",16)
TANGO_COLOR_ORANGE_DARK = int("ce5c00ff",16)
TANGO_COLOR_CHOCOLATE_LIGHT = int("e9b96eff",16)
TANGO_COLOR_CHOCOLATE_MID = int("c17d11ff",16)
TANGO_COLOR_CHOCOLATE_DARK = int("8f5902ff",16)
TANGO_COLOR_CHAMELEON_LIGHT = int("8ae234ff",16)
TANGO_COLOR_CHAMELEON_MID = int("73d216ff",16)
TANGO_COLOR_CHAMELEON_DARK = int("4e9a06ff",16)
TANGO_COLOR_SKYBLUE_LIGHT = int("729fcfff",16)
TANGO_COLOR_SKYBLUE_MID = int("3465a4ff",16)
TANGO_COLOR_SKYBLUE_DARK = int("204a87ff",16)
TANGO_COLOR_PLUM_LIGHT = int("ad7fa8ff",16)
TANGO_COLOR_PLUM_MID = int("75507bff",16)
TANGO_COLOR_PLUM_DARK = int("5c3566ff",16)
TANGO_COLOR_SCARLETRED_LIGHT = int("ef2929ff",16)
TANGO_COLOR_SCARLETRED_MID = int("cc0000ff",16)
TANGO_COLOR_SCARLETRED_DARK = int("a40000ff",16)
TANGO_COLOR_ALUMINIUM1_LIGHT = int("eeeeecff",16)
TANGO_COLOR_ALUMINIUM1_MID = int("d3d7cfff",16)
TANGO_COLOR_ALUMINIUM1_DARK = int("babdb6ff",16)
TANGO_COLOR_ALUMINIUM2_LIGHT = int("888a85ff",16)
TANGO_COLOR_ALUMINIUM2_MID = int("555753ff",16)
TANGO_COLOR_ALUMINIUM2_DARK = int("2e3436ff",16)

#Style elements common to ConduitCanvasItem and DPCanvasItem
SIDE_PADDING = 10.0
LINE_WIDTH = 3.0
RECTANGLE_RADIUS = 5.0

class Canvas(goocanvas.Canvas):
    """
    This class manages many objects
    """
    
    INITIAL_WIDTH = 600
    INITIAL_HEIGHT = 450
    CANVAS_WIDTH = 450
    CANVAS_HEIGHT = 600
    WELCOME_MESSAGE = _("Drag a Dataprovider here to continue")

    def __init__(self, parentWindow, typeConverter, syncManager, dataproviderMenu, conduitMenu):
        """
        Draws an empty canvas of the appropriate size
        """
        #setup the canvas
        goocanvas.Canvas.__init__(self)
        self.set_size_request(Canvas.INITIAL_WIDTH, Canvas.INITIAL_HEIGHT)
        self.set_bounds(0, 0, Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        self.root = self.get_root_item()

        self.sync_manager = syncManager
        self.typeConverter = typeConverter
        self.parentWindow = parentWindow
        self._setup_popup_menus(dataproviderMenu, conduitMenu)
        
        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.on_drag_motion)
        self.connect('size-allocate', self._canvas_resized)
        self.connect('item-created', self._on_item_created)

        #Show a friendly welcome message on the canvas the first time the
        #application is launched
        self.welcomeMessage = None

        #keeps a reference to the currently selected (most recently clicked)
        #canvas items
        self.selectedConduitItem = None
        self.selectedDataproviderItem = None

        #model is a SyncSet, not set till later because it is loaded from xml
        self.model = None

        #Keep a list of dataproviders that could not be added because they
        #were unavailable, and should instead be added when they become
        #available (via callback)
        self.pendingDataproviderWrappers = {}

        self._add_welcome_message()
        self.show()

    def _on_item_created(self, *args):
        #FIXME: This is never called.....
        #If it is then we could connect menu callbacks here
        print "-------------- CREATED ------------------------------------------"

    def _add_welcome_message(self):
        """
        Adds a friendly welcome message to the canvas.
        
        Does so only if there are no conduits, otherwise it would just
        get in the way.
        """
        if self.welcomeMessage == None:
                if self.model == None or (self.model != None and self.model.num_conduits() == 0):
                    self.welcomeMessage = goocanvas.Text(  
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

    def _delete_welcome_message(self):
        """
        Removes the welcome message from the canvas if it has previously
        been added
        """
        if self.welcomeMessage != None:
            self.root.remove_child(self.root.find_child(self.welcomeMessage))
            del(self.welcomeMessage)
            self.welcomeMessage = None

    def _get_child_conduit_items(self):
        items = []
        for i in range(0, self.root.get_n_children()):
            condItem = self.root.get_child(i)
            if isinstance(condItem, ConduitCanvasItem):
                items.append(condItem)
        return items

    def _canvas_resized(self, widget, allocation):
        for i in self._get_child_conduit_items():
            i.set_width(allocation.width)

    def _on_conduit_button_press(self, view, target, event):
        """
        Handle button clicks on conduits
        """
        #right click
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.selectedConduitItem = view
            if event.button == 3:
                #Preset the two way menu items sensitivity
                if not self.selectedConduitItem.model.can_do_two_way_sync():
                    self.twoWayMenuItem.set_property("sensitive", False)
                else:
                    self.twoWayMenuItem.set_property("sensitive", True)
                #Set item ticked if two way sync enabled
                self.twoWayMenuItem.set_active(self.selectedConduitItem.model.twoWaySyncEnabled)
                #Set item ticked if two way sync enabled
                self.slowSyncMenuItem.set_active(self.selectedConduitItem.model.slowSyncEnabled)
                #Show the menu                
                if not self.selectedConduitItem.model.is_busy():
                    self.conduitMenu.popup(
                                                None, None, 
                                                None, event.button, event.time
                                                )
        #dont propogate the event                
        return True

    def _on_dataprovider_button_press(self, view, target, event):
        """
        Handle button clicks
        
        @param user_data_dataprovider_wrapper: The dpw that was clicked
        @type user_data_dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        #single right click
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.selectedDataproviderItem = view
            if event.button == 3:
                if view.model.enabled and not view.model.module.is_busy():
                    #show the menu
                    self.dataproviderMenu.popup(
                                None, None, 
                                None, event.button, event.time
                                )

        #double left click
        elif event.type == gtk.gdk._2BUTTON_PRESS:
            self.selectedDataproviderItem = view
            if event.button == 1:
                if view.model.enabled and not view.model.module.is_busy():
                    #configure the DP
                    self.on_configure_item_clicked(None)

        #dont propogate the event
        return True

    def _get_bottom_of_conduits_coord(self):
        """
        Gets the Y coordinate at the bottom of all visible conduits
        
        @returns: A coordinate (postivive down) from the canvas origin
        @rtype: C{int}
        """
        y = 0.0
        for i in self._get_child_conduit_items():
            y = y + i.get_height()
        return y

    def _add_conduit_canvas_item(self, conduitModel):
        """
        Creates a ConduitCanvasItem and adds it to the canvas
        """
        c_x,c_y,c_w,c_h = self.get_bounds()
        #Create the item and move it into position
        bottom = self._get_bottom_of_conduits_coord()
        item = ConduitCanvasItem(
                        parent=self.root, 
                        model=conduitModel,
                        width=c_w)
        item.connect('button-press-event', self._on_conduit_button_press)
        item.translate(
                LINE_WIDTH,
                bottom+LINE_WIDTH
                )
        return item

    def _delete_conduit_canvas_item(self, conduitCanvasItem):
        """
        Removes a conduit canvas item from the canvas, and its model 
        from the syncset
        """
        cond = conduitCanvasItem.model
        logw("Deleting conduit")
        #remove the views, then the model
        idx = self.root.find_child(conduitCanvasItem)
        if idx != -1:
            self.root.remove_child(idx)
            self.model.remove_conduit(cond)
        else:
            logw("Error finding item")
        self._add_welcome_message()

    def _add_dataprovider_to_conduit_canvas_item(self, conduitCanvasItem, dataproviderWrapper):
        """
        Creates a DataProviderCanvasItem and adds it to the conduitCanvasItem
        and model
        """
        #If module is None we store a reference to the conduit that holds the
        #dp and replace it later.
        if dataproviderWrapper == None:
            log("Dataprovider %s unavailable. Adding pending its availability" % key)
            dataproviderWrapper = PendingDataproviderWrapper(key)
            #Store the pending element so it can be removed later            
            self.pendingDataproviderWrappers[key] = dataproviderWrapper

        item = DataProviderCanvasItem(
                            parent=conduitCanvasItem, 
                            model=dataproviderWrapper
                            )
        item.connect('button-press-event', self._on_dataprovider_button_press)

        conduitCanvasItem.model.add_dataprovider(dataproviderWrapper)
        conduitCanvasItem.add_dataprovider_canvas_item(item)

    def _remove_overlap(self):
        """
        Moves the ConduitCanvasItems to stop them overlapping visually
        """
        items = self._get_child_conduit_items()
        if len(items) > 1:
            for i in xrange(1, len(items)):
                overlap = items[i-1].get_bottom() - items[i].get_top()
                print "Overlap: %s %s ----> %s" % (overlap,i-1,i)
                if overlap != 0.0:
                    #translate all those below
                    for item in items[i:]:
                        item.translate(0,overlap)

    def get_sync_set(self):
        """
        Returns the conduits to be synchronized
        @todo: Should there be any processing in this function???
        
        @returns: A list of conduits to synchronize
        @rtype: C{Conduit[]}
        """        
        return self.model

    def set_sync_set(self, syncSet):
        self.model = syncSet
        for c in self.model.get_all_conduits():
            print "RESTORING CONDUIT: ", c
            conduitCanvasItem = self._add_conduit_canvas_item(c)
            for dp in c.get_all_dataproviders():
                print "RESTORING DP", dp
                self._add_dataprovider_to_conduit_canvas_item(conduitCanvasItem, dp)

        if self.model.num_conduits() > 0:
            self._delete_welcome_message()
        self._add_welcome_message()
        
    def on_drag_motion(self, wid, context, x, y, time):
        """
        on_drag_motion
        """
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def _setup_popup_menus(self, dataproviderPopupXML, conduitPopupXML):
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

        #connect the menu callbacks
        conduitPopupXML.signal_autoconnect(self)
        dataproviderPopupXML.signal_autoconnect(self)        


    def on_delete_group_clicked(self, widget):
        """
        Delete a conduit and all its associated dataproviders
        """
        conduitCanvasItem = self.selectedConduitItem
        self._delete_conduit_canvas_item(conduitCanvasItem)
        self._remove_overlap()

    def on_refresh_group_clicked(self, widget):
        """
        Call the initialize method on all dataproviders in the conduit
        """
        if self.selectedConduitItem.model.datasource is not None and len(self.selectedConduitItem.model.datasinks) > 0:
            self.sync_manager.refresh_conduit(self.selectedConduitItem.model)
        else:
            log("Conduit must have a datasource and a datasink")
    
    def on_synchronize_group_clicked(self, widget):
        """
        Synchronize the selected conduit
        """
        if self.selectedConduitItem.model.datasource is not None and len(self.selectedConduitItem.model.datasinks) > 0:
            self.sync_manager.sync_conduit(self.selectedConduitItem.model)
        else:
            log("Conduit must have a datasource and a datasink")
        
    def on_delete_item_clicked(self, widget):
        """
        Delete the selected dataprovider
        """
        dp = self.selectedDataproviderItem.model
        dpCanvasItem = self.selectedDataproviderItem
        conduitCanvasItem = dpCanvasItem.get_parent()
        cond = conduitCanvasItem.model

        #first remove the views, then from the models
        conduitCanvasItem.delete_dataprovider_canvas_item(dpCanvasItem)
        cond.delete_dataprovider(dp)

        if cond.is_empty():
            self._delete_conduit_canvas_item(conduitCanvasItem)
            
        self._remove_overlap()

    def on_configure_item_clicked(self, widget):
        """
        Calls the C{configure(window)} method on the selected dataprovider
        """
        
        dp = self.selectedDataproviderItem.model.module
        log("Configuring %s" % dp)
        #May block
        dp.configure(self.parentWindow)

    def on_refresh_item_clicked(self, widget):
        """
        Refreshes a single dataprovider
        """
        dp = self.selectedDataproviderItem.model
        if dp != None:
            self.sync_manager.refresh_dataprovider(dp)

    def on_two_way_sync_toggle(self, widget):
        """
        Enables or disables two way sync on dataproviders.
        """
        if widget.get_active():
            self.selectedConduitItem.model.enable_two_way_sync()
        else:
            self.selectedConduitItem.model.disable_two_way_sync()

    def on_slow_sync_toggle(self, widget):
        """
        Enables or disables slow sync of dataproviders.
        """
        if widget.get_active():
            self.selectedConduitItem.model.enable_slow_sync()
        else:
            self.selectedConduitItem.model.disable_slow_sync()

    def check_pending_dataproviders(self, wrapper):
        """
        When a dataprovider is added, replace any active instances 
        of PendingDataProvider for that type with a real DataProvider

        @param wrapper: The dataprovider wrapper to insert on canvas in 
        place of a Pending DP
        @type wrapper: L{conduit.Module.ModuleWrapper}
        """
        key = wrapper.get_key()
        if key in self.pendingDataproviderWrappers:
            for item in self._get_child_conduit_items():
                c = item.model
                pending = self.pendingDataproviderWrappers[key]
                if c.has_dataprovider(pending):
                    #delete old one
                    c.delete_dataprovider(pending)

                    #add new one
                    c.add_dataprovider(wrapper)
                    item.sourceItem.set_model(wrapper)

            del self.pendingDataproviderWrappers[key]

    def make_pending_dataproviders(self, wrapper):
        """
        When a dataprovider is removed, replace any active instances 
        with a PendingDataProvider

        @param wrapper: The dataprovider wrapper to replace with a Pending DP
        @type wrapper: L{conduit.Module.ModuleWrapper} 
        """
        log("Replacing all instances of %s with a PendingDataProvider" % wrapper.get_key())
        for item in self._get_child_conduit_items():
            c = item.model
            for dp in c.get_dataproviders_by_key(wrapper.get_key()):
                logd("Found matching dp (%s), make pending!" % dp)
                pendingWrapper = PendingDataproviderWrapper(wrapper.get_key())
                self.pendingDataproviderWrappers[wrapper.get_key()] = pendingWrapper

                c.delete_dataprovider(dp)
                item.sourceItem.set_model(pendingWrapper)

    def add_dataprovider_to_canvas(self, key, dataproviderWrapper, x, y):
        """
        Adds a new dataprovider to the Canvas
        
        @param module: The dataprovider wrapper to add to the canvas
        @type module: L{conduit.Module.ModuleWrapper}. If this is None then
        a placeholder should be added (which will get replaced later if/when
        the actual dataprovider becomes available. 
        See self.pendingDataproviderWrappers
        @param x: The x location on the canvas to place the module widget
        @type x: C{int}
        @param y: The y location on the canvas to place the module widget
        @type y: C{int}
        @returns: The conduit that the dataprovider was added to
        """
        self._delete_welcome_message()

        existing = self.get_item_at(x,y,False)
        c_x,c_y,c_w,c_h = self.get_bounds()

        if existing == None:
            cond = Conduit()
            self.model.add_conduit(cond)
            item = self._add_conduit_canvas_item(cond)

            #now add a dataprovider to the conduit
            self._add_dataprovider_to_conduit_canvas_item(item,dataproviderWrapper)
        else:
            parent = existing.get_parent()
            while parent != None and not isinstance(parent, ConduitCanvasItem):
                parent = parent.get_parent()
            
            if parent != None:
                self._add_dataprovider_to_conduit_canvas_item(parent,dataproviderWrapper)

            self._remove_overlap()

    def clear_canvas(self):
        for c in self._get_child_conduit_items():
            self._delete_conduit_canvas_item(c)

class _CanvasItem(goocanvas.Group):
    def __init__(self, parent, model):
        #FIXME: If parent is None in base constructor then goocanvas segfaults
        #this means a ref to items may be kept so this may leak...
        goocanvas.Group.__init__(self, parent=parent)
        self.model = model

    def get_height(self):
        b = goocanvas.Bounds()
        self.get_bounds(b)
        return b.y2-b.y1

    def get_width(self):
        b = goocanvas.Bounds()
        self.get_bounds(b)
        return b.x2-b.x1

    def get_top(self):
        b = goocanvas.Bounds()
        self.get_bounds(b)
        return b.y1

    def get_bottom(self):
        b = goocanvas.Bounds()
        self.get_bounds(b)
        return b.y2

    def get_left(self):
        b = goocanvas.Bounds()
        self.get_bounds(b)
        return b.x1

    def get_right(self):
        b = goocanvas.Bounds()
        self.get_bounds(b)
        return b.x2

class DataProviderCanvasItem(_CanvasItem):

    WIDGET_WIDTH = 130
    WIDGET_HEIGHT = 60
    IMAGE_TO_TEXT_PADDING = 5
    PENDING_MESSAGE = "Pending"
    PENDING_FILL_COLOR = TANGO_COLOR_BUTTER_LIGHT
    SOURCE_FILL_COLOR = TANGO_COLOR_ALUMINIUM1_MID
    SINK_FILL_COLOR = TANGO_COLOR_SKYBLUE_LIGHT
    TWOWAY_FILL_COLOR = TANGO_COLOR_BUTTER_MID

    def __init__(self, parent, model):
        _CanvasItem.__init__(self, parent, model)
        self.set_model(model)

        self._build_widget()

    def _get_fill_color(self):
        if self.model.module == None:
            return DataProviderCanvasItem.PENDING_FILL_COLOR
        else:
            if self.model.module_type == "source":
                return DataProviderCanvasItem.SOURCE_FILL_COLOR
            elif self.model.module_type == "sink":
                return DataProviderCanvasItem.SINK_FILL_COLOR
            elif self.model.module_type == "twoway":
                return DataProviderCanvasItem.TWOWAY_FILL_COLOR
            else:
                logw("Unknown module type: Cannot get fill color")

    def _build_widget(self):
        if self.model.module == None:
            statusText = DataProviderCanvasItem.PENDING_MESSAGE
        else:
            statusText = self.model.module.get_status_text()

        fillColor = self._get_fill_color()

        self.box = goocanvas.Rect(   
                                x=0, 
                                y=0, 
                                width=DataProviderCanvasItem.WIDGET_WIDTH-(2*LINE_WIDTH), 
                                height=DataProviderCanvasItem.WIDGET_HEIGHT-(2*LINE_WIDTH),
                                line_width=LINE_WIDTH, 
                                stroke_color="black",
                                fill_color_rgba=fillColor, 
                                radius_y=RECTANGLE_RADIUS, 
                                radius_x=RECTANGLE_RADIUS
                                )
        pb = self.model.get_icon()
        pbx = int((1*DataProviderCanvasItem.WIDGET_WIDTH/5) - (pb.get_width()/2))
        pby = int((1*DataProviderCanvasItem.WIDGET_HEIGHT/3) - (pb.get_height()/2))
        image = goocanvas.Image(pixbuf=pb,
                                x=pbx,
                                y=pby
                                )
        name = goocanvas.Text(  x=pbx + pb.get_width() + DataProviderCanvasItem.IMAGE_TO_TEXT_PADDING, 
                                y=int(1*DataProviderCanvasItem.WIDGET_HEIGHT/3), 
                                width=3*DataProviderCanvasItem.WIDGET_WIDTH/5, 
                                text=self.model.name, 
                                anchor=gtk.ANCHOR_WEST, 
                                font="Sans 8"
                                )
        self.statusText = goocanvas.Text(  
                                x=int(1*DataProviderCanvasItem.WIDGET_WIDTH/10), 
                                y=int(2*DataProviderCanvasItem.WIDGET_HEIGHT/3), 
                                width=4*DataProviderCanvasItem.WIDGET_WIDTH/5, 
                                text=statusText, 
                                anchor=gtk.ANCHOR_WEST, 
                                font="Sans 7",
                                fill_color_rgba=TANGO_COLOR_ALUMINIUM2_MID,
                                )                                    
        
           
        #Add all the visual elements which represent a dataprovider    
        self.add_child(self.box)
        self.add_child(name)
        self.add_child(image)
        self.add_child(self.statusText) 

    def _on_change_detected(self, dataprovider):
        print "CHANGE DETECTED"

    def _on_status_changed(self, dataprovider):
        msg = dataprovider.get_status_text()
        self.statusText.set_property("text", msg)

    def set_model(self, model):
        self.model = model
        if self.model.module != None:
            self.model.module.connect("change-detected", self._on_change_detected)
            self.model.module.connect("status-changed", self._on_status_changed)
        else:
            self.statusText.set_property("text", DataProviderCanvasItem.PENDING_MESSAGE)
            fillColor = self._get_fill_color()
            self.box.set_property("fill_color_rgba", fillColor)
    
class ConduitCanvasItem(_CanvasItem):

    WIDGET_HEIGHT = 100

    def __init__(self, parent, model, width):
        _CanvasItem.__init__(self, parent, model)

        self.model.connect("parameters-changed", self._on_conduit_parameters_changed)

        self.sourceItem = None
        self.sinkDpItems = []
        self.connectorItems = {}

        #Build the widget
        self._build_widget(width)

    def _position_dataprovider(self, dpCanvasItem):
        dpx, dpy = self.model.get_dataprovider_position(dpCanvasItem.model)
        if dpx == 0:
            #Its a source
            dpCanvasItem.translate(
                        SIDE_PADDING,
                        SIDE_PADDING + self.l.get_property("line_width")
                        )
        else:
            #Its a sink
            if dpy == 0:
                i = SIDE_PADDING
            else:
                i = (dpy * SIDE_PADDING) + SIDE_PADDING

            dpCanvasItem.translate(
                            self.get_width() - dpCanvasItem.get_width() - SIDE_PADDING,
                            (dpy * dpCanvasItem.get_height()) + i + self.l.get_property("line_width")
                            )

    def _build_widget(self, width):
        true_width = width-(2*LINE_WIDTH) #account for line width

        #draw a spacer to give some space between conduits
        points = goocanvas.Points([(0.0, 0.0), (true_width, 0.0)])
        self.l = goocanvas.Polyline(points=points, line_width=LINE_WIDTH, stroke_color="white")
        self.add_child(self.l)

        #draw a box which will contain the dataproviders
        self.bounding_box = goocanvas.Rect(
                                x=0, 
                                y=5, 
                                width=true_width,     
                                height=ConduitCanvasItem.WIDGET_HEIGHT,
                                line_width=LINE_WIDTH, 
                                stroke_color="black",
                                fill_color_rgba=TANGO_COLOR_ALUMINIUM1_LIGHT, 
                                radius_y=RECTANGLE_RADIUS, 
                                radius_x=RECTANGLE_RADIUS
                                )
        self.add_child(self.bounding_box)

    def _resize_height(self):
        sourceh =   0.0
        sinkh =     0.0
        padding =   0.0
        for dpw in self.sinkDpItems:
            sinkh += dpw.get_height()
        #padding between items
        numSinks = len(self.sinkDpItems)
        if numSinks:
            sinkh += ((numSinks - 1)*SIDE_PADDING)
        if self.sourceItem != None:
            sourceh += self.sourceItem.get_height()

        self.set_height(
                    max(sourceh, sinkh)+    #expand to the largest
                    (1.5*SIDE_PADDING)        #padding at the top and bottom
                    )

    def _delete_connector(self, item):
        """
        Deletes the connector associated with the sink item
        """
        try:
            connector = self.connectorItems[item]
            idx = self.find_child(connector)
            if idx != -1:
                self.remove_child(idx)
            else:
                logw("Could not find child connector item")
            
            del(self.connectorItems[item])
        except KeyError: pass

    def _on_conduit_parameters_changed(self, cond):
        #update the twowayness of the connectors
        for c in self.connectorItems.values():
            c.set_two_way(self.model.is_two_way())

    def add_dataprovider_canvas_item(self, item):
        self._position_dataprovider(item)

        #is it a sink or a source?
        dpx, dpy = self.model.get_dataprovider_position(item.model)
        if dpx == 0:
            self.sourceItem = item
        else:
            self.sinkDpItems.append(item)

        #now resize the bounding box to fit all the dataproviders
        self._resize_height()

        #add a connector. If we just added a source then we need to make all the
        #connectors, otherwise we just need to add a connector for the new item
        if dpx == 0:
            fromx = self.sourceItem.get_right()
            fromy = self.sourceItem.get_top() + (self.sourceItem.get_height()/2)
            #make all the connectors
            for s in self.sinkDpItems:
                tox = s.get_left()
                toy = s.get_top() + (s.get_height()/2)
                c = ConnectorCanvasItem(self,
                    fromx,
                    fromy-self.get_top(),
                    tox,
                    toy-self.get_top(),
                    self.model.is_two_way(),
                    False
                    )
                self.connectorItems[s] = c
        else:
            #just make the new connector
            if self.sourceItem != None:
                fromx = self.sourceItem.get_right()
                fromy = self.sourceItem.get_top() + (self.sourceItem.get_height()/2)
                tox = item.get_left()
                toy = item.get_top() + (item.get_height()/2)
                c = ConnectorCanvasItem(self,
                    fromx,
                    fromy-self.get_top(),
                    tox,
                    toy-self.get_top(),
                    self.model.is_two_way(),
                    False
                    )
                self.connectorItems[item] = c

    def delete_dataprovider_canvas_item(self, item):
        """
        Removes the DataProviderCanvasItem and its connectors
        """
        idx = self.find_child(item)
        if idx != -1:
            self.remove_child(idx)
        else:
            logw("Could not find child dataprovider item")

        if item == self.sourceItem:
            self.sourceItem = None
            #remove all connectors (copy because we modify in place)   
            for item in self.connectorItems.copy():
                self._delete_connector(item)
        else:
            self.sinkDpItems.remove(item)
            self._delete_connector(item)

        self._resize_height()

    def set_height(self, h):
        self.bounding_box.set_property("height",h)

    def set_width(self, w):
        true_width = w-(2*LINE_WIDTH)

        #resize the box
        self.bounding_box.set_property("width",true_width)
        #resize the spacer
        p = goocanvas.Points([(0.0, 0.0), (true_width, 0.0)])
        self.l.set_property("points",p)

        for d in self.sinkDpItems:
            desired = w - d.get_width() - SIDE_PADDING
            actual = d.get_left()
            change = desired-actual
            #print "%s v %s" % (desired-actual,w - self.get_width())
            #move righthand dp
            d.translate(change, 0)
            #resize arrow
            self.connectorItems[d].resize_connector_width(change)

class ConnectorCanvasItem(_CanvasItem):

    CONNECTOR_RADIUS = 30
    CONNECTOR_LINE_WIDTH = 5
    CONNECTOR_YOFFSET = 20
    CONNECTOR_TEXT_XPADDING = 5
    CONNECTOR_TEXT_YPADDING = 10

    def __init__(self, parent, fromX, fromY, toX, toY, twoway, lossy):
        _CanvasItem.__init__(self, parent, None)
    
        self.fromX = fromX
        self.fromY = fromY
        self.toX = toX
        self.toY = toY

        self.twoway = twoway
        self.lossy = lossy

        self._build_widget()
        
    def _build_widget(self):
        self.left_end_round = goocanvas.Ellipse(
                                    center_x=self.fromX, 
                                    center_y=self.fromY, 
                                    radius_x=6, 
                                    radius_y=6, 
                                    fill_color="black", 
                                    line_width=0.0
                                    )
        points = goocanvas.Points([(self.fromX-6, self.fromY), (self.fromX-7, self.fromY)])
        self.left_end_arrow = goocanvas.Polyline(
                            points=points,
                            stroke_color="black",
                            line_width=5,
                            end_arrow=True,
                            arrow_tip_length=3,
                            arrow_length=3,
                            arrow_width=3
                            )

        

        points = goocanvas.Points([(self.toX-1, self.toY), (self.toX, self.toY)])
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
        self.add_child(self.right_end,-1)

        self.path = goocanvas.Path(data="",stroke_color="black",line_width=ConnectorCanvasItem.CONNECTOR_LINE_WIDTH)
        self._draw_path()

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
            self.add_child(self.left_end_arrow,-1)
        else:
            self.add_child(self.left_end_round,-1)

    def _draw_path(self):
        """
        Builds a SVG path statement. This represents the (optionally) curved 
        connector between a datasource and datasink. Then assigns the path
        to the internal path object
        """
        if self.fromY == self.toY:
            #draw simple straight line
            p = "M%s,%s "           \
                "L%s,%s "       %   (
                                    self.fromX,self.fromY,  #absolute start point
                                    self.toX,self.toY       #absolute line to point
                                    )
        else:
            #draw pretty curvy line 
            r = ConnectorCanvasItem.CONNECTOR_RADIUS  #radius of curve
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

        pidx = self.find_child(self.path)
        if pidx != -1:
            self.remove_child(pidx)

        #Reecreate the path to work round goocanvas bug
        self.path = goocanvas.Path(data=p,stroke_color="black",line_width=ConnectorCanvasItem.CONNECTOR_LINE_WIDTH)
        self.add_child(self.path,-1)
            
    def resize_connector_width(self, dw):
        """
        Adjusts the size of the connector. Used when the window is resized
        
        @param dw: The change in width
        @type dw: C{int}
        """
        #Only the X location changes
        if dw != 0:
            self.toX += dw
            self._draw_path()
            self._draw_arrow_ends()

    def set_color(self, color):
        """
        @param color: The connectors new color
        @type color: C{string}
        """
        self.path.set_property("stroke_color",color)
        self.left_end_arrow.set_property("stroke_color",color)
        #FIXME: Causes segfault
        #self.left_end_round.set_property("fill_color",color)
        self.right_end.set_property("stroke_color",color)        

    def set_two_way(self, twoway):
        """
        @param color: The connectors new color
        @type color: C{string}
        """
        self.twoway = twoway
        self._draw_arrow_ends()

class PendingDataproviderWrapper(ModuleWrapper):
    def __init__(self, key):
        ModuleWrapper.__init__(
                    self,
                    "name", 
                    "description",
                    "gtk-missing",          #use a missing image
                    "twoway",               #twoway so can placehold as source or sink
                    "category", 
                    "in_type",
                    "out_type",
                    key.split(':')[0],
                    (),
                    None,
                    False)                  #enabled = False so a sync is not performed
        self.key = key

    def get_key(self):
        return self.key

