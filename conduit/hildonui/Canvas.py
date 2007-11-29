"""
Manages adding, removing, resizing and drawing the canvas

The Canvas is the main area in Conduit, the area to which DataProviders are 
dragged onto.

Copyright: John Stowers, 2006
License: GPLv2
"""
import goocanvas
import gobject
import gtk
import pango
from gettext import gettext as _
import logging
log = logging.getLogger("hildon.Canvas")

import conduit
from conduit.Conduit import Conduit
from conduit.hildonui.List import DND_TARGETS
import conduit.gtkui.Canvas 

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
TRANSPARENT_COLOR = int("00000000",16)

#Style elements common to ConduitCanvasItem and DPCanvasItem
SIDE_PADDING = 10.0
LINE_WIDTH = 3.0
RECTANGLE_RADIUS = 5.0

#GRR support api break in pygoocanvas 0.6/8.0 -> 0.9.0
NEW_GOOCANVAS_API = goocanvas.pygoocanvas_version >= (0,9,0)

class Canvas(goocanvas.Canvas, gobject.GObject):
    """
    This class manages many objects
    """
    CANVAS_WIDTH = 450
    CANVAS_HEIGHT = 450
    WELCOME_MESSAGE = _("Drag a Dataprovider here to continue")

    __gsignals__ = {
        "position-changed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])    # The canvas
    }

    def __init__(self, parentWindow, typeConverter, syncManager):
        """
        Draws an empty canvas of the appropriate size
        """
        #setup the canvas
        goocanvas.Canvas.__init__(self)
        self.set_bounds(0, 0, Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        self.set_size_request(Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        self.root = self.get_root_item()

        self.sync_manager = syncManager
        self.typeConverter = typeConverter
        self.parentWindow = parentWindow

        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.on_drag_motion)

        #Show a friendly welcome message on the canvas the first time the
        #application is launched
        self.welcomeMessage = None

        #keeps a reference to the currently selected (most recently clicked)
        #canvas items
        self.selectedConduitItem = None
        self.selectedDataproviderItem = None

        #model is a SyncSet, not set till later because it is loaded from xml
        self.model = None
        self.position = -1

    def _show_welcome_message(self):
        """
        Adds a friendly welcome message to the canvas.
        
        Does so only if there are no conduits, otherwise it would just
        get in the way.
        """
        if self.welcomeMessage == None:
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

        idx = self.root.find_child(self.welcomeMessage)
        if self.model == None or (self.model != None and self.model.num_conduits() == 0):
            if idx == -1:
                self.root.add_child(self.welcomeMessage,-1)
        else:
            if idx != -1:
                self.root.remove_child(idx)

    def _delete_welcome_message(self):
        """
        Removes the welcome message from the canvas if it has previously
        been added
        """
        if self.welcomeMessage != None:
            
            del(self.welcomeMessage)
            self.welcomeMessage = None

    def _get_child_conduit_canvas_items(self):
        items = []
        for i in range(0, self.root.get_n_children()):
            condItem = self.root.get_child(i)
            if isinstance(condItem, ConduitCanvasItem):
                items.append(condItem)
        return items

    def _get_child_conduit_canvas_item(self):
        for i in range(0, self.root.get_n_children()):
            condItem = self.root.get_child(i)
            if isinstance(condItem, ConduitCanvasItem):
                return condItem

        return None

    def _get_child_dataprovider_canvas_items(self):
        items = []

        conduitItem = self._get_child_conduit_canvas_item()

        if conduitItem:
            for i in range(0, conduitItem.get_n_children()):
                dpItem = conduitItem.get_child(i)
                if isinstance(dpItem, DataProviderCanvasItem):
                    items.append(dpItem)
        return items

    def _on_dataprovider_button_press(self, view, target, event):
        """
        Handle button clicks
        
        @param user_data_dataprovider_wrapper: The dpw that was clicked
        @type user_data_dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        self.selectedDataproviderItem = view

        #single right click
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 3:
                if view.model.enabled and not view.model.module.is_busy():
                    #show the menu
                    self.dataproviderMenu.popup(
                                None, None, 
                                None, event.button, event.time
                                )

        #double left click
        elif event.type == gtk.gdk._2BUTTON_PRESS:
            if event.button == 1:
                if view.model.enabled and not view.model.module.is_busy():
                    #configure the DP
                    self.on_configure_dataprovider_clicked(None)

        #dont propogate the event
        return True

    def _get_bottom_of_conduits_coord(self):
        """
        Gets the Y coordinate at the bottom of all visible conduits
        
        @returns: A coordinate (postivive down) from the canvas origin
        @rtype: C{int}
        """
        y = 0.0
        for i in self._get_child_conduit_canvas_items():
            y = y + i.get_height()
        return y

    def on_conduit_removed(self, sender, conduitRemoved):
        self.move_previous ()

    def on_conduit_added(self, sender, conduitAdded):
        """
        Creates a ConduitCanvasItem for the new conduit
        """
        log.debug("Conduit added %s" % conduitAdded)

        self.set_position(self.model.index(conduitAdded))
        
    def _create_item_for_conduit (self, conduit):
        c_x,c_y,c_w,c_h = self.get_bounds()
        #Create the item and move it into position
        bottom = self._get_bottom_of_conduits_coord()
        conduitCanvasItem = ConduitCanvasItem(
                                parent=self.root, 
                                model=conduit,
                                width=c_w)
        conduitCanvasItem.translate(
                LINE_WIDTH/2.0,
                bottom+(LINE_WIDTH/2.0)
                )

        #log.debug("Width = %s,%s,%s,%s" % self.get_bounds())

        #FIXME Evilness to fix ConduitCanvasItems ending up too big (scrollbars suck!) 
        #self.set_size_request(Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        #self.set_size_request(Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)

        for dp in conduit.get_all_dataproviders():
            self.on_dataprovider_added(None, dp, conduitCanvasItem)

        conduit.connect("dataprovider-added", self.on_dataprovider_added, conduitCanvasItem)
        conduit.connect("dataprovider-removed", self.on_dataprovider_removed, conduitCanvasItem)

        self._show_welcome_message()

    def on_dataprovider_removed(self, sender, dataproviderRemoved, conduitCanvasItem):
        for item in self._get_child_dataprovider_canvas_items():
            if item.model == dataproviderRemoved:
                conduitCanvasItem.delete_dataprovider_canvas_item(item)
        self._remove_overlap()
        self._show_welcome_message()

    def on_dataprovider_added(self, sender, dataproviderAdded, conduitCanvasItem):
        """
        Creates a DataProviderCanvasItem for the new dataprovider and adds it to
        the canvas
        """

        #check for duplicates to eliminate race condition in set_sync_set
        if dataproviderAdded in [i.model for i in self._get_child_dataprovider_canvas_items()]:
            return

        item = DataProviderCanvasItem(
                            parent=conduitCanvasItem, 
                            model=dataproviderAdded
                            )
        item.connect('button-press-event', self._on_dataprovider_button_press)
        conduitCanvasItem.add_dataprovider_canvas_item(item)
        self._remove_overlap()
        self._show_welcome_message()

    def _remove_overlap(self):
        """
        Moves the ConduitCanvasItems to stop them overlapping visually
        """
        items = self._get_child_conduit_canvas_items()
        if len(items) > 0:
            #special case where the top one was deleted
            top = items[0].get_top()-(LINE_WIDTH/2)
            if top != 0.0:
                for item in items:
                    #translate all those below
                    item.translate(0,-top)
            else:
                for i in xrange(0, len(items)):
                    try:
                        overlap = items[i].get_bottom() - items[i+1].get_top()
                        log.debug("Overlap: %s %s ----> %s" % (overlap,i,i+1))
                        if overlap != 0.0:
                            #translate all those below
                            for item in items[i+1:]:
                                item.translate(0,overlap)
                    except IndexError: 
                        break


    def get_sync_set(self):
        return self.model

    def set_sync_set(self, syncSet):
        self.model = syncSet

        conduits = self.model.get_all_conduits()
        
        if len(conduits) > 0:
            self.set_position(0)

        self.model.connect("conduit-added", self.on_conduit_added)
        self.model.connect("conduit-removed", self.on_conduit_removed)

        self._show_welcome_message()

    def _refresh_current_item(self):
        self._remove_current_item()

        try:
            conduit = self.model.get_conduit(self.position)
            self._create_item_for_conduit (conduit)
        except:
            self._show_welcome_message()            

    def move_next(self):
        self.set_position(self.position + 1)

    def move_previous(self):
        self.set_position(self.position - 1)

    def set_position (self, index):
        nr_of_conduits = self.model.num_conduits()

        if index > nr_of_conduits:
            return

        # get the old one
        if self.position == index:
            return

        # set new index
        self.position = index

        log.debug("Current position %d, Lenght: %d" % (self.position, nr_of_conduits))

        # position cycling
        if self.position == nr_of_conduits:
            self.position = 0
        elif self.position < 0:
            self.position = nr_of_conduits - 1

        self._refresh_current_item()

        self.emit("position-changed")

    def get_position (self):
        return self.position
        
    def get_position_str(self):
        return "%s/%s" % (self.position + 1, self.model.num_conduits())

    def get_current(self):
        return self.model.get_conduit(self.position)        

    def _remove_current_item (self):
        currentItem = self._get_child_conduit_canvas_item()

        if not currentItem:
            return

        #remove the canvas item
        idx = self.root.find_child(currentItem)
        if idx != -1:
            self.root.remove_child(idx)
        else:
            log.warn("Error finding item")

        self._remove_overlap()
        self._show_welcome_message()
        
    def on_drag_motion(self, wid, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def on_configure_dataprovider_clicked(self, widget):
        """
        Calls the configure method on the selected dataprovider
        """
        dp = self.selectedDataproviderItem.model.module
        log.info("Configuring %s" % dp)
        #May block
        dp.configure(self.parentWindow)

    def on_refresh_dataprovider_clicked(self, widget):
        """
        Refreshes a single dataprovider
        """
        dp = self.selectedDataproviderItem.model
        #dp.module.refresh()
        cond = self.selectedConduitItem.model
        cond.refresh_dataprovider(dp)

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

    def add_dataprovider_to_canvas(self, key, dataproviderWrapper, x, y):
        """
        Adds a new dataprovider to the Canvas
        
        @param module: The dataprovider wrapper to add to the canvas
        @type module: L{conduit.Module.ModuleWrapper}. 
        @param x: The x location on the canvas to place the module widget
        @type x: C{int}
        @param y: The y location on the canvas to place the module widget
        @type y: C{int}
        @returns: The conduit that the dataprovider was added to
        """
        existing = self.get_item_at(x,y,False)
        c_x,c_y,c_w,c_h = self.get_bounds()

        #if the user dropped on the right half of the canvas try add into the sink position
        if x < (c_w/2):
            trySourceFirst = True
        else:
            trySourceFirst = False

        if existing == None:
            cond = Conduit(self.sync_manager)
            cond.add_dataprovider(dataproviderWrapper, trySourceFirst)
            self.model.add_conduit(cond)

        else:
            parent = existing.get_parent()
            while parent != None and not isinstance(parent, ConduitCanvasItem):
                parent = parent.get_parent()
            
            if parent != None:
                parent.model.add_dataprovider(dataproviderWrapper, trySourceFirst)

    def clear_canvas(self):
        self.model.clear()

class DataProviderCanvasItem(conduit.gtkui.Canvas.DataProviderCanvasItem):
    WIDGET_WIDTH = 160
    WIDGET_HEIGHT = 85

    NAME_FONT = "Sans 12"
    STATUS_FONT = "Sans 10"

class ConduitCanvasItem(conduit.gtkui.Canvas.ConduitCanvasItem):
    pass 

class ConnectorCanvasItem(conduit.gtkui.Canvas.ConnectorCanvasItem):
    pass

