"""
Manages adding, removing, resizing and drawing the canvas

The Canvas is the main area in Conduit, the area to which DataProviders are 
dragged onto.

Copyright: John Stowers, 2006
Copyright: Thomas Van Machelen, 2007
License: GPLv2
"""
import goocanvas
import gobject
import gtk
import pango
from gettext import gettext as _
import logging
log = logging.getLogger("hildonui.Canvas")

import conduit
from conduit.Conduit import Conduit
from conduit.hildonui.List import DND_TARGETS
import conduit.gtkui.Canvas 

LINE_WIDTH = 3.0

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

    # Setup
    #######
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

        # dp context menu
        self.dataproviderMenu = DataProviderMenu(self)
        # conduit context menu
        self.conduitMenu = ConduitMenu(self)
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

    # Button press events on canvas items
    #####################################
    def _on_conduit_button_press(self, view, target, event):        
        log.debug("Clicked View: %s" % view.model)

        #single left click
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            if not view.model.is_busy():
                self.conduitMenu.popup(None, None, 
                                       None, event.button, event.time)

        #dont propogate the event
        return True

    def _on_dataprovider_button_press(self, view, target, event):
        """
        Handle button clicks
        
        @param user_data_dataprovider_wrapper: The dpw that was clicked
        @type user_data_dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        log.debug("Clicked View: %s" % view.model)
        self.selectedDataproviderItem = view

        #single left click
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            if view.model.enabled and not view.model.module.is_busy():
                self.dataproviderMenu.popup(None, None, 
                                            None, event.button, event.time)

        #dont propogate the event
        return True
       
    # Syncset signal callbacks        
    ##########################
    def on_conduit_added(self, sender, conduitAdded):
        """
        Creates a ConduitCanvasItem for the new conduit
        """
        log.debug("Conduit added %s" % conduitAdded)

        self.set_position(self.model.index(conduitAdded))
 
    def on_conduit_removed(self, sender, conduitRemoved):
        self.move_previous ()

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

    def on_dataprovider_removed(self, sender, dataproviderRemoved, conduitCanvasItem):
        for item in self._get_child_dataprovider_canvas_items():
            if item.model == dataproviderRemoved:
                conduitCanvasItem.delete_dataprovider_canvas_item(item)
        self._remove_overlap()
        self._show_welcome_message()

    # Drag & Drop
    #############
    def on_drag_motion(self, wid, context, x, y, time):
        """
        Sets the status on dragging
        """
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

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

    # Canvas operations
    ###################
    def clear_canvas(self):
        self.model.clear()

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

    def move_next(self):
        """
        Moves the canvas to the next conduit
        """
        self.set_position(self.position + 1)

    def move_previous(self):
        """
        Moves the canvas to the previous conduit
        """
        self.set_position(self.position - 1)

    def set_position (self, index):
        """
        Sets the Canvas position to the index provided
        """
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
        """
        Gets the position
        """
        return self.position
        
    def get_position_str(self):
        """
        Gets the position representation
        """
        return "%s/%s" % (self.position + 1, self.model.num_conduits())

    def sync_all(self):
        for conduit in self.model.get_all_conduits():
            if conduit.datasource is not None and len(conduit.datasinks) > 0:
                self.sync_manager.sync_conduit(conduit)
            else:
                log.info("Conduit must have a datasource and a datasink")        

    # Item Creation and Drawing
    ###########################
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


    def _refresh_current_item(self):
        """
        Refreshes the current item; only in drawing, not the conduit
        """
        self._remove_current_item()

        try:
            conduit = self.model.get_conduit(self.position)
            self._create_item_for_conduit (conduit)
        except:
            self._show_welcome_message()            

    def _remove_current_item (self):
        """
        Clears the current conduit from the Canvas
        """
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

        # keep ref
        self.selectedConduitItem = conduitCanvasItem

        #FIXME Evilness to fix ConduitCanvasItems ending up too big (scrollbars suck!) 
        #self.set_size_request(Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)
        #self.set_size_request(Canvas.CANVAS_WIDTH, Canvas.CANVAS_HEIGHT)

        conduitCanvasItem.connect('button-press-event', self._on_conduit_button_press)

        for dp in conduit.get_all_dataproviders():
            self.on_dataprovider_added(None, dp, conduitCanvasItem)

        conduit.connect("dataprovider-added", self.on_dataprovider_added, conduitCanvasItem)
        conduit.connect("dataprovider-removed", self.on_dataprovider_removed, conduitCanvasItem)

        self._show_welcome_message()

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

 
    # def on_two_way_sync_toggle(self, widget):
    #     """
    #     Enables or disables two way sync on dataproviders.
    #     """
    #     if widget.get_active():
    #         self.selectedConduitItem.model.enable_two_way_sync()
    #     else:
    #         self.selectedConduitItem.model.disable_two_way_sync()

    # def on_slow_sync_toggle(self, widget):
    #     """
    #     Enables or disables slow sync of dataproviders.
    #     """
    #     if widget.get_active():
    #         self.selectedConduitItem.model.enable_slow_sync()
    #     else:
    #         self.selectedConduitItem.model.disable_slow_sync()

class DataProviderCanvasItem(conduit.gtkui.Canvas.DataProviderCanvasItem):
    WIDGET_WIDTH = 160
    WIDGET_HEIGHT = 85

    NAME_FONT = "Sans 12"
    STATUS_FONT = "Sans 10"

    # def _get_icon(self):
    #     return self.model.get_icon(24)

class ConduitCanvasItem(conduit.gtkui.Canvas.ConduitCanvasItem):
    pass 

class ConnectorCanvasItem(conduit.gtkui.Canvas.ConnectorCanvasItem):
    pass

class ContextMenu(gtk.Menu):
    def __init__(self):
        gtk.Menu.__init__(self)    

    def _add_menu_item (self, text, activate_cb):
        item = gtk.MenuItem(_(text))
        item.connect("activate", activate_cb)
        self.append(item)

class ConduitMenu(ContextMenu):
    def __init__(self, canvas):
        ContextMenu.__init__(self)
        self.canvas = canvas

        self._add_menu_item("Refresh", self._on_conduit_refresh)
        self._add_menu_item("Synchronize", self._on_conduit_sync)

        self.show_all()

    def _on_conduit_refresh(self, menuItem):
        conduit = self.canvas.selectedConduitItem.model
        conduit.refresh()

    def _on_conduit_sync(self, menuItem):
        conduit = self.canvas.selectedConduitItem.model
        conduit.sync()

class DataProviderMenu(ContextMenu):
    def __init__(self, canvas):
        ContextMenu.__init__(self)
        self.canvas = canvas

        self._add_menu_item("Configure", self._on_configure_activate)
        self._add_menu_item("Refresh", self._on_refresh_activate)
        self.append(gtk.SeparatorMenuItem())
        self._add_menu_item("Delete", self._on_delete_activate)

        self.show_all()

    def _on_configure_activate(self, menuItem):
        dp = self.canvas.selectedDataproviderItem.model.module

        log.debug("Configuring %s " % dp)
        dp.configure(self.canvas.parentWindow)

    def _on_refresh_activate(self, menuItem):
        dp = self.canvas.selectedDataproviderItem.model
        cond = self.canvas.selectedConduitItem.model
        cond.refresh_dataprovider(dp)

    def _on_delete_activate(self, menuItem):
        dp = self.canvas.selectedDataproviderItem.model
        cond = self.canvas.selectedConduitItem.model
        cond.delete_dataprovider(dp)

