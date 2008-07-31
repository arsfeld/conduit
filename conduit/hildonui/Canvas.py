"""
Manages adding, removing, resizing and drawing the canvas

The Canvas is the main area in Conduit, the area to which DataProviders are 
dragged onto.

Copyright: John Stowers, 2006
Copyright: Thomas Van Machelen, 2007
License: GPLv2
"""
import gobject
import gtk
import logging
log = logging.getLogger("hildonui.Canvas")

import conduit.gtkui.Canvas
import conduit.gtkui.Util as GtkUtil 

LINE_WIDTH = 3.0

class Canvas(conduit.gtkui.Canvas.Canvas, gobject.GObject):
    """
    This class manages many objects
    """

    __gsignals__ = {
        "position-changed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])    # The canvas
    }

    def __init__(self, parentWindow, typeConverter, syncManager):
        """
        Draws an empty canvas of the appropriate size
        """
        #setup the canvas
        conduit.gtkui.Canvas.Canvas.__init__(self,
                                parentWindow,typeConverter,syncManager,
                                #menus are set in _setup_popup_menus
                                None,None)
        self.position = -1
        
    def _setup_popup_menus(self, dataproviderPopupXML, conduitPopupXML):
        # dp context menu
        self.dataproviderMenu = DataProviderMenu(self)
        # conduit context menu
        self.conduitMenu = ConduitMenu(self)
        
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
                self.dataproviderMenu.configureMenuItem.set_property("sensitive", view.model.configurable)
                self.dataproviderMenu.popup(None, None, 
                                            None, event.button, event.time)

        #dont propogate the event
        return True
       
    def on_conduit_added(self, sender, conduitAdded):
        """
        Creates a ConduitCanvasItem for the new conduit
        """
        log.debug("Conduit added %s" % conduitAdded)
        self.set_position(self.model.index(conduitAdded))
 
    def on_conduit_removed(self, sender, conduitRemoved):
        self.move_previous ()

    def set_sync_set(self, syncSet):
        conduit.gtkui.Canvas.Canvas.set_sync_set(self, syncSet)
        if len(self.model.get_all_conduits()) > 0:
            self.set_position(0)

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
        #self.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        #self.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)

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

    def get_style_properties(self, specifier):
        if specifier == "box":
            #color the box differently if it is pending
            if self.model.module == None:
                color = GtkUtil.TANGO_COLOR_BUTTER_LIGHT
            else:
                if self.model.module_type == "source":
                    color = GtkUtil.TANGO_COLOR_ALUMINIUM1_MID
                elif self.model.module_type == "sink":
                    color = GtkUtil.TANGO_COLOR_SKYBLUE_LIGHT
                elif self.model.module_type == "twoway":
                    color = GtkUtil.TANGO_COLOR_BUTTER_MID
                else:
                    color = None
        
            kwargs = {
                "stroke_color":"black",
                "fill_color_rgba":color
            }
        elif specifier == "name":
            kwargs = {
                "font":"Sans 8"
            }
        elif specifier == "statusText":
            kwargs = {
                "font":"Sans 7",
                "fill_color_rgba":GtkUtil.TANGO_COLOR_ALUMINIUM2_MID
            }
        
        return kwargs

class ConduitCanvasItem(conduit.gtkui.Canvas.ConduitCanvasItem):

    def get_style_properties(self, specifier):
        if specifier == "boundingBox":
            kwargs = {
                "fill_color_rgba":GtkUtil.TANGO_COLOR_ALUMINIUM1_LIGHT, 
                "stroke_color":"black"
            }
        elif specifier == "progressText":
            kwargs = {
                "font":"Sans 7",
                "fill_color":"black"
            }
        else:
            kwargs = {}

class ConnectorCanvasItem(conduit.gtkui.Canvas.ConnectorCanvasItem):
    pass

class ContextMenu(gtk.Menu):
    def __init__(self):
        gtk.Menu.__init__(self)    

    def _add_menu_item (self, text, activate_cb):
        item = gtk.MenuItem(text)
        item.connect("activate", activate_cb)
        self.append(item)
        return item

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

        self.configureMenuItem = self._add_menu_item("Configure", self._on_configure_activate)
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

