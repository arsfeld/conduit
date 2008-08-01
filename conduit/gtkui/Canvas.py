"""
Manages adding, removing, resizing and drawing the canvas

The Canvas is the main area in Conduit, the area to which DataProviders are 
dragged onto.

Copyright: John Stowers, 2006
License: GPLv2
"""
import cairo
import goocanvas
import gtk
import pango
from gettext import gettext as _

import logging
log = logging.getLogger("gtkui.Canvas")

import conduit.utils as Utils
import conduit.Conduit as Conduit
import conduit.gtkui.Tree
import conduit.gtkui.Util as GtkUtil

log.info("Module Information: %s" % Utils.get_module_information(goocanvas, "pygoocanvas_version"))

class _StyleMixin:

    STYLES = (
        "fg",
        "bg",
        "light",
        "dark",
        "mid",
        "text",
        "base",
        "text_aa"
        )
    STYLE_STATES = (
        "normal",
        "active",
        "prelight",
        "selected",
        "insensitive"
        )
        
    def _get_colors_and_state(self, styleName, stateName):
        style = self.get_gtk_style()
        if style:
            colors = getattr(style, styleName.lower(), None)
            state = getattr(gtk, "STATE_%s" % stateName.upper(), None)
        else:
            colors = None
            state = None

        return colors,state

    def get_gtk_style(self):
        """
        @returns: The gtk.Style for the widget
        """
        #not that clean, we can be mixed into the
        #canvas, or a canvas item
        try:
            return self.get_canvas().style
        except AttributeError:
            try:
                return self.style
            except AttributeError:
                return None

    def get_style_color_rgb(self, styleName, stateName):
        colors,state = self._get_colors_and_state(styleName, stateName)
        if colors != None and state != None:
            return GtkUtil.gdk2rgb(colors[state])
        else:
            return GtkUtil.gdk2rgb(GtkUtil.str2gdk("red"))
        
    def get_style_color_rgba(self, styleName, stateName, a=1):
        colors,state = self._get_colors_and_state(styleName, stateName)
        if colors != None and state != None:
            return GtkUtil.gdk2rgba(colors[state], a)
        else:
            return GtkUtil.gdk2rgba(GtkUtil.str2gdk("red"), a)
            
    def get_style_color_int_rgb(self, styleName, stateName):
        colors,state = self._get_colors_and_state(styleName, stateName)
        if colors != None and state != None:
            return GtkUtil.gdk2intrgb(colors[state])
        else:
            return GtkUtil.gdk2intrgb(GtkUtil.str2gdk("red"))
            
    def get_style_color_int_rgba(self, styleName, stateName, a=1):
        colors,state = self._get_colors_and_state(styleName, stateName)
        if colors != None and state != None:
            return GtkUtil.gdk2intrgba(colors[state], int(a*255))
        else:
            return GtkUtil.gdk2intrgba(GtkUtil.str2gdk("red"), int(a*255))

class _CanvasItem(goocanvas.Group, _StyleMixin):

    #attributes common to Conduit and Dataprovider items
    RECTANGLE_RADIUS =  4.0

    def __init__(self, parent, model):
        #FIXME: If parent is None in base constructor then goocanvas segfaults
        #this means a ref to items may be kept so this may leak...
        goocanvas.Group.__init__(self, parent=parent)
        self.model = model
        
        #this little piece of magic re-applies style properties to the
        #widgets, when the users theme changes
        canv = self.get_canvas()
        if canv:
            canv.connect("style-set", self._automatic_style_updater)

    def _automatic_style_updater(self, *args):
        if not self.get_gtk_style():
            #while in the midst of changing theme, the style is sometimes
            #None, but dont worry, we will get called again
            return
        for attr in self.get_styled_item_names():
            item = getattr(self, attr, None)
            if item:
                item.set_properties(
                        **self.get_style_properties(attr)
                        )

    def get_height(self):
        b = self.get_bounds()
        return b.y2-b.y1

    def get_width(self):
        b = self.get_bounds()
        return b.x2-b.x1

    def get_top(self):
        b = self.get_bounds()
        return b.y1

    def get_bottom(self):
        b = self.get_bounds()
        return b.y2

    def get_left(self):
        b = self.get_bounds()
        return b.x1

    def get_right(self):
        b = self.get_bounds()
        return b.x2
        
    def get_styled_item_names(self):
        raise NotImplementedError        
        
    def get_style_properties(self, specifier):
        raise NotImplementedError

class Canvas(goocanvas.Canvas, _StyleMixin):
    """
    This class manages many objects
    """
    DND_TARGETS = [
        ('conduit/element-name', 0, 0)
    ]

    WELCOME_MESSAGE = _("Drag a Data Provider here to continue")
    def __init__(self, parentWindow, typeConverter, syncManager, dataproviderMenu, conduitMenu):
        """
        Draws an empty canvas of the appropriate size
        """
        #setup the canvas
        goocanvas.Canvas.__init__(self)
        self.set_bounds(0, 0, 
                conduit.GLOBALS.settings.get("gui_initial_canvas_width"),
                conduit.GLOBALS.settings.get("gui_initial_canvas_height")
                )
        self.set_size_request(
                conduit.GLOBALS.settings.get("gui_initial_canvas_width"),
                conduit.GLOBALS.settings.get("gui_initial_canvas_height")
                )
        self.root = self.get_root_item()

        self.sync_manager = syncManager
        self.typeConverter = typeConverter
        self.parentWindow = parentWindow

        self._setup_popup_menus(dataproviderMenu, conduitMenu)

        #set up DND from the treeview
        self.drag_dest_set(  gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                        self.DND_TARGETS,
                        gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        self.connect('drag-motion', self.on_drag_motion)
        self.connect('size-allocate', self._canvas_resized)

        #track theme chages for canvas background
        self.connect('realize', self._update_for_theme)
        #We need a flag becuase otherwise we recurse forever.
        #It appears that setting background_color_rgb in the 
        #sync-set handler causes sync-set to be emitted again, and again...
        self._changing_style = False
        self.connect("style-set", self._update_for_theme)

        #keeps a reference to the currently selected (most recently clicked)
        #canvas items
        self.selectedConduitItem = None
        self.selectedDataproviderItem = None

        #model is a SyncSet, not set till later because it is loaded from xml
        self.model = None
        
        #Show a friendly welcome message on the canvas the first time the
        #application is launched
        self.welcomeMessage = None
        self._show_welcome_message()
        
    def _update_for_theme(self, *args):
        if not self.get_gtk_style() or self._changing_style:
            return

        self._changing_style = True    
        self.set_property(
                "background_color_rgb",
                self.get_style_color_int_rgb("bg","normal")
                )
        if self.welcomeMessage:
            self.welcomeMessage.set_property(
                "fill_color_rgba",
                self.get_style_color_int_rgba("text","normal")
                )
        self._changing_style = False

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

        self.dataproviderMenu = dataproviderPopupXML.get_widget("DataProviderMenu")
        self.configureMenuItem = dataproviderPopupXML.get_widget("configure")

        self.conduitMenu = conduitPopupXML.get_widget("ConduitMenu")
        self.twoWayMenuItem = conduitPopupXML.get_widget("two_way_sync")
        self.slowSyncMenuItem = conduitPopupXML.get_widget("slow_sync")
        self.autoSyncMenuItem = conduitPopupXML.get_widget("auto_sync")

        self.twoWayMenuItem.connect("toggled", self.on_two_way_sync_toggle)
        self.slowSyncMenuItem.connect("toggled", self.on_slow_sync_toggle)
        self.autoSyncMenuItem.connect("toggled", self.on_auto_sync_toggle)

        #connect the conflict popups
        self.policyWidgets = {}
        for policyName in Conduit.CONFLICT_POLICY_NAMES:
            for policyValue in Conduit.CONFLICT_POLICY_VALUES:
                widgetName = "%s_%s" % (policyName,policyValue)
                #store the widget and connect to toggled signal
                widget = conduitPopupXML.get_widget(widgetName)
                widget.connect("toggled", self.on_policy_toggle, policyName, policyValue)
                self.policyWidgets[widgetName] = widget
                
        #connect the menu callbacks
        conduitPopupXML.signal_autoconnect(self)
        dataproviderPopupXML.signal_autoconnect(self)

    def _show_welcome_message(self):
        """
        Adds a friendly welcome message to the canvas.
        
        Does so only if there are no conduits, otherwise it would just
        get in the way.
        """
        if self.welcomeMessage == None:
            c_x,c_y,c_w,c_h = self.get_bounds()
            self.welcomeMessage = goocanvas.Text(  
                                    x=c_w/2, 
                                    y=c_w/3, 
                                    width=3*c_w/5, 
                                    text=self.WELCOME_MESSAGE, 
                                    anchor=gtk.ANCHOR_CENTER,
                                    alignment=pango.ALIGN_CENTER,
                                    font="Sans 10",
                                    fill_color_rgba=self.get_style_color_int_rgba("text","normal"),
                                    )

        idx = self.root.find_child(self.welcomeMessage)
        if self.model == None or (self.model != None and self.model.num_conduits() == 0):
            if idx == -1:
                self.root.add_child(self.welcomeMessage,-1)
        else:
            if idx != -1:
                self.root.remove_child(idx)
                self.welcomeMessage = None

    def _get_child_conduit_canvas_items(self):
        items = []
        for i in range(0, self.root.get_n_children()):
            condItem = self.root.get_child(i)
            if isinstance(condItem, ConduitCanvasItem):
                items.append(condItem)
        return items

    def _get_child_dataprovider_canvas_items(self):
        items = []
        for c in self._get_child_conduit_canvas_items():
            for i in range(0, c.get_n_children()):
                dpItem = c.get_child(i)
                if isinstance(dpItem, DataProviderCanvasItem):
                    items.append(dpItem)
        return items

    def _canvas_resized(self, widget, allocation):
        self.set_bounds(
                    0,0,
                    allocation.width,
                    self._get_minimum_canvas_size(allocation.height)
                    )
        for i in self._get_child_conduit_canvas_items():
            i.set_width(allocation.width)

    def _on_conduit_button_press(self, view, target, event):
        """
        Handle button clicks on conduits
        """
        self.selectedConduitItem = view

        #right click
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 3:
                #Preset the two way menu items sensitivity
                if not self.selectedConduitItem.model.can_do_two_way_sync():
                    self.twoWayMenuItem.set_property("sensitive", False)
                else:
                    self.twoWayMenuItem.set_property("sensitive", True)
                #Set item ticked if two way sync enabled
                self.twoWayMenuItem.set_active(self.selectedConduitItem.model.is_two_way())
                #Set item ticked if two way sync enabled
                self.slowSyncMenuItem.set_active(self.selectedConduitItem.model.slowSyncEnabled)
                #Set item ticked if two way sync enabled
                self.autoSyncMenuItem.set_active(self.selectedConduitItem.model.autoSyncEnabled)
                #Set the conflict and delete policy
                for policyName in Conduit.CONFLICT_POLICY_NAMES:
                    policyValue = self.selectedConduitItem.model.get_policy(policyName)
                    widgetName = "%s_%s" % (policyName,policyValue)
                    self.policyWidgets[widgetName].set_active(True)

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
        self.selectedDataproviderItem = view
        self.selectedConduitItem = view.get_parent()

        #single right click
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 3:
                if view.model.enabled and not view.model.module.is_busy():
                    self.configureMenuItem.set_property("sensitive", view.model.configurable)
                    #show the menu
                    self.dataproviderMenu.popup(
                                None, None, 
                                None, event.button, event.time
                                )

        #double left click
        elif event.type == gtk.gdk._2BUTTON_PRESS:
            if event.button == 1:
                if view.model.enabled and not view.model.module.is_busy():
                    if view.model.configurable:
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
        
    def _get_minimum_canvas_size(self, allocH=None):
        if not allocH:
            allocH = self.get_allocation().height
    
        bottom = self._get_bottom_of_conduits_coord()
        return max(bottom + ConduitCanvasItem.WIDGET_HEIGHT + 20, allocH)
        
    def _remove_overlap(self):
        """
        Moves the ConduitCanvasItems to stop them overlapping visually
        """
        items = self._get_child_conduit_canvas_items()
        if len(items) > 0:
            #special case where the top one was deleted
            top = items[0].get_top()-(items[0].LINE_WIDTH/2)
            if top != 0.0:
                for item in items:
                    #translate all those below
                    item.translate(0,-top)
            else:
                for i in xrange(0, len(items)):
                    try:
                        overlap = items[i].get_bottom() - items[i+1].get_top()
                        if overlap != 0.0:
                            #translate all those below
                            for item in items[i+1:]:
                                item.translate(0,overlap)
                    except IndexError: 
                        break

    def on_conduit_removed(self, sender, conduitRemoved):
        for item in self._get_child_conduit_canvas_items():
            if item.model == conduitRemoved:
                #remove the canvas item
                idx = self.root.find_child(item)
                if idx != -1:
                    self.root.remove_child(idx)
                else:
                    log.warn("Error finding item")
        self._remove_overlap()

        self._show_welcome_message()
        c_x,c_y,c_w,c_h = self.get_bounds()
        self.set_bounds(
                    0,
                    0,
                    c_w,
                    self._get_minimum_canvas_size()
                    )

    def on_conduit_added(self, sender, conduitAdded):
        """
        Creates a ConduitCanvasItem for the new conduit
        """
        #check for duplicates to eliminate race condition in set_sync_set
        if conduitAdded in [i.model for i in self._get_child_conduit_canvas_items()]:
            return

        c_x,c_y,c_w,c_h = self.get_bounds()
        #Create the item and move it into position
        bottom = self._get_bottom_of_conduits_coord()
        conduitCanvasItem = ConduitCanvasItem(
                                parent=self.root, 
                                model=conduitAdded,
                                width=c_w)
        conduitCanvasItem.connect('button-press-event', self._on_conduit_button_press)
        conduitCanvasItem.translate(
                conduitCanvasItem.LINE_WIDTH/2.0,
                bottom+(conduitCanvasItem.LINE_WIDTH/2.0)
                )

        for dp in conduitAdded.get_all_dataproviders():
            self.on_dataprovider_added(None, dp, conduitCanvasItem)

        conduitAdded.connect("dataprovider-added", self.on_dataprovider_added, conduitCanvasItem)
        conduitAdded.connect("dataprovider-removed", self.on_dataprovider_removed, conduitCanvasItem)

        self._show_welcome_message()
        self.set_bounds(
                    0,
                    0,
                    c_w,
                    self._get_minimum_canvas_size()
                    )

    def on_dataprovider_removed(self, sender, dataproviderRemoved, conduitCanvasItem):
        for item in self._get_child_dataprovider_canvas_items():
            if item.model == dataproviderRemoved:
                conduitCanvasItem.delete_dataprovider_canvas_item(item)
        self._remove_overlap()

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

    def get_sync_set(self):
        return self.model

    def set_sync_set(self, syncSet):
        self.model = syncSet
        for c in self.model.get_all_conduits():
            self.on_conduit_added(None, c)

        self.model.connect("conduit-added", self.on_conduit_added)
        self.model.connect("conduit-removed", self.on_conduit_removed)

    def on_drag_motion(self, wid, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def on_delete_conduit_clicked(self, widget):
        """
        Delete a conduit and all its associated dataproviders
        """
        conduitCanvasItem = self.selectedConduitItem
        cond = conduitCanvasItem.model
        self.model.remove_conduit(cond)

    def on_refresh_conduit_clicked(self, widget):
        """
        Refresh the selected conduit
        """
        self.selectedConduitItem.model.refresh()
    
    def on_synchronize_conduit_clicked(self, widget):
        """
        Synchronize the selected conduit
        """
        self.selectedConduitItem.model.sync()
        
    def on_delete_dataprovider_clicked(self, widget):
        """
        Delete the selected dataprovider
        """
        dp = self.selectedDataproviderItem.model
        conduitCanvasItem = self.selectedDataproviderItem.get_parent()
        cond = conduitCanvasItem.model
        cond.delete_dataprovider(dp)

    def on_configure_dataprovider_clicked(self, widget):
        """
        Calls the configure method on the selected dataprovider
        """
        dp = self.selectedDataproviderItem.model.module
        log.info("Configuring %s" % dp)
        #May block
        dp.configure(self.parentWindow)
        self.selectedDataproviderItem.update_appearance()

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

    def on_auto_sync_toggle(self, widget):
        """
        Enables or disables slow sync of dataproviders.
        """
        if widget.get_active():
            self.selectedConduitItem.model.enable_auto_sync()
        else:
            self.selectedConduitItem.model.disable_auto_sync()

    def on_policy_toggle(self, widget, policyName, policyValue):
        if widget.get_active():
            self.selectedConduitItem.model.set_policy(policyName, policyValue)

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
            cond = Conduit.Conduit(self.sync_manager)
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

class DataProviderCanvasItem(_CanvasItem):

    WIDGET_WIDTH = 130
    WIDGET_HEIGHT = 60
    IMAGE_TO_TEXT_PADDING = 5
    PENDING_MESSAGE = "Pending"
    MAX_TEXT_LENGTH = 10
    MAX_TEXT_LINES = 2
    LINE_WIDTH = 2.0

    def __init__(self, parent, model):
        _CanvasItem.__init__(self, parent, model)

        self._build_widget()
        self.set_model(model)
        
    def _get_model_name(self):
        #FIXME: Goocanvas.Text does not ellipsize text,
        #so we do it...... poorly
        text = ""
        lines = 1
        for word in self.model.get_name().split(" "):
            if len(word) > self.MAX_TEXT_LENGTH:
                word = word[0:self.MAX_TEXT_LENGTH] + "... "
            else:
                word = word + " "

            #gross guess for how much of the space we have used
            if (len(text)+len(word))  > (self.MAX_TEXT_LENGTH*self.MAX_TEXT_LINES):
                #append final elipsis
                if not word.endswith("... "):
                    text = text + "..."
                break
            else:
                text = text + word
            
        return text

    def _get_icon(self):
        return self.model.get_icon()        

    def _build_widget(self):
        self.box = goocanvas.Rect(   
                                x=0, 
                                y=0, 
                                width=self.WIDGET_WIDTH-(2*self.LINE_WIDTH), 
                                height=self.WIDGET_HEIGHT-(2*self.LINE_WIDTH),
                                radius_y=self.RECTANGLE_RADIUS, 
                                radius_x=self.RECTANGLE_RADIUS,
                                **self.get_style_properties("box")
                                )
        pb = self.model.get_icon()
        pbx = int((1*self.WIDGET_WIDTH/5) - (pb.get_width()/2))
        pby = int((1*self.WIDGET_HEIGHT/3) - (pb.get_height()/2))
        self.image = goocanvas.Image(pixbuf=pb,
                                x=pbx,
                                y=pby
                                )
        self.name = goocanvas.Text(
                                x=pbx + pb.get_width() + self.IMAGE_TO_TEXT_PADDING, 
                                y=int(1*self.WIDGET_HEIGHT/3), 
                                width=3*self.WIDGET_WIDTH/5, 
                                text=self._get_model_name(), 
                                anchor=gtk.ANCHOR_WEST,
                                **self.get_style_properties("name")
                                )
        self.statusText = goocanvas.Text(  
                                x=int(1*self.WIDGET_WIDTH/10), 
                                y=int(2*self.WIDGET_HEIGHT/3), 
                                width=4*self.WIDGET_WIDTH/5, 
                                text="", 
                                anchor=gtk.ANCHOR_WEST, 
                                **self.get_style_properties("statusText")
                                )                                    
        
        #Add all the visual elements which represent a dataprovider    
        self.add_child(self.box)
        self.add_child(self.name)
        self.add_child(self.image)
        self.add_child(self.statusText) 

    def _on_change_detected(self, dataprovider):
        log.debug("CHANGE DETECTED")

    def _on_status_changed(self, dataprovider):
        msg = dataprovider.get_status()
        self.statusText.set_property("text", msg)
    
    def get_styled_item_names(self):
        return "box","name","statusText"
        
    def get_style_properties(self, specifier):
        if specifier == "box":
            #color the box differently if it is pending, i.e. unavailable,
            #disconnected, etc.
            if self.model.module == None:
                insensitive = self.get_style_color_int_rgba("mid","insensitive")
                kwargs = {
                    "line_width":1.5,
                    "stroke_color_rgba":insensitive,
                    "fill_color_rgba":insensitive
                }
                
            else:
                pattern = cairo.LinearGradient(0, 0, 0, 100)
                pattern.add_color_stop_rgb(
                                        0,
                                        *self.get_style_color_rgb("dark","active")
                                        );
                pattern.add_color_stop_rgb(
                                        0.5,
                                        *self.get_style_color_rgb("dark","prelight")
                                        );
            
                kwargs = {
                    "line_width":2.0,
                    "stroke_color":"black",
                    "fill_pattern":pattern
                }
        elif specifier == "name":
            kwargs = {
                "font":"Sans 8",
                "fill_color_rgba":self.get_style_color_int_rgba("text","normal")
            }
        elif specifier == "statusText":
            kwargs = {
                "font":"Sans 7",
                "fill_color_rgba":self.get_style_color_int_rgba("text_aa","normal")
            }
        
        return kwargs
        
    def update_appearance(self):
        #the image
        pb = self._get_icon()
        pbx = int((1*self.WIDGET_WIDTH/5) - (pb.get_width()/2))
        pby = int((1*self.WIDGET_HEIGHT/3) - (pb.get_height()/2))
        self.image.set_property("pixbuf",pb)

        self.name.set_property("text",self._get_model_name())

        if self.model.module == None:
            statusText = self.PENDING_MESSAGE
        else:
            statusText = self.model.module.get_status()
        self.statusText.set_property("text",statusText)

        self.box.set_properties(
                    **self.get_style_properties("box")
                    )

    def set_model(self, model):
        self.model = model
        self.update_appearance()
        if self.model.module != None:
            self.model.module.connect("change-detected", self._on_change_detected)
            self.model.module.connect("status-changed", self._on_status_changed)
    
class ConduitCanvasItem(_CanvasItem):

    DIVIDER = False
    FLAT_BOX = True
    WIDGET_HEIGHT = 100
    SIDE_PADDING = 10.0
    LINE_WIDTH = 2.0

    def __init__(self, parent, model, width):
        _CanvasItem.__init__(self, parent, model)

        self.model.connect("parameters-changed", self._on_conduit_parameters_changed)
        self.model.connect("dataprovider-changed", self._on_conduit_dataprovider_changed)
        self.model.connect("sync-progress", self._on_conduit_progress)

        self.sourceItem = None
        self.sinkDpItems = []
        self.connectorItems = {}

        self.l = None
        self.progressText = None
        self.boundingBox = None        

        #if self.DIVIDER, show an transparent bouding box, and a
        #simple dividing line
        self.divider = None
        #goocanvas.Points need a list of tuples, not a list of lists. Yuck
        self.dividerPoints = [(),()]

        #Build the widget
        self._build_widget(width)

    def _add_progress_text(self):
        if self.sourceItem != None and len(self.sinkDpItems) > 0:
            if self.progressText == None:
                fromx,fromy,tox,toy = self._get_connector_coordinates(self.sourceItem,self.sinkDpItems[0])
                self.progressText = goocanvas.Text(  
                                    x=fromx+5, 
                                    y=fromy-15, 
                                    width=100, 
                                    text="", 
                                    anchor=gtk.ANCHOR_WEST,
                                    alignment=pango.ALIGN_LEFT,
                                    **self.get_style_properties("progressText")
                                    )
                self.add_child(self.progressText) 

    def _position_dataprovider(self, dpCanvasItem):
        dpx, dpy = self.model.get_dataprovider_position(dpCanvasItem.model)
        if dpx == 0:
            #Its a source
            dpCanvasItem.translate(
                        self.SIDE_PADDING,
                        self.SIDE_PADDING + self.l.get_property("line_width")
                        )
        else:
            #Its a sink
            if dpy == 0:
                i = self.SIDE_PADDING
            else:
                i = (dpy * self.SIDE_PADDING) + self.SIDE_PADDING

            dpCanvasItem.translate(
                            self.get_width() - dpCanvasItem.get_width() - self.SIDE_PADDING,
                            (dpy * dpCanvasItem.get_height()) + i + self.l.get_property("line_width")
                            )

    def _build_widget(self, width):
        true_width = width-self.LINE_WIDTH

        #draw a spacer to give some space between conduits
        points = goocanvas.Points([(0.0, 0.0), (true_width, 0.0)])
        self.l = goocanvas.Polyline(
                                points=points,
                                line_width=self.LINE_WIDTH,
                                stroke_color_rgba=GtkUtil.TRANSPARENT_COLOR
                                )
        self.add_child(self.l)

        #draw a box which will contain the dataproviders
        self.boundingBox = goocanvas.Rect(
                                x=0, 
                                y=5, 
                                width=true_width,     
                                height=self.WIDGET_HEIGHT,
                                radius_y=self.RECTANGLE_RADIUS, 
                                radius_x=self.RECTANGLE_RADIUS,
                                **self.get_style_properties("boundingBox")
                                )
        self.add_child(self.boundingBox)
        if self.DIVIDER:
            #draw an underline
            #from point
            self.dividerPoints[0] = (true_width*0.33,5+self.WIDGET_HEIGHT)
            self.dividerPoints[1] = (2*(true_width*0.33),5+self.WIDGET_HEIGHT)
            
            self.divider = goocanvas.Polyline(
                                    points=goocanvas.Points(self.dividerPoints),
                                    **self.get_style_properties("divider")
                                    )
            self.add_child(self.divider)

    def _resize_height(self):
        sourceh =   0.0
        sinkh =     0.0
        padding =   0.0
        for dpw in self.sinkDpItems:
            sinkh += dpw.get_height()
        #padding between items
        numSinks = len(self.sinkDpItems)
        if numSinks:
            sinkh += ((numSinks - 1)*self.SIDE_PADDING)
        if self.sourceItem != None:
            sourceh += self.sourceItem.get_height()

        self.set_height(
                    max(sourceh, sinkh)+        #expand to the largest
                    (1.5*self.SIDE_PADDING)        #padding at the top and bottom
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
                log.warn("Could not find child connector item")
            
            del(self.connectorItems[item])
        except KeyError: pass

    def _on_conduit_parameters_changed(self, cond):
        self.update_appearance()

    def _on_conduit_dataprovider_changed(self, cond, olddpw, newdpw):
        for item in [self.sourceItem] + self.sinkDpItems:
            if item.model.get_key() == olddpw.get_key():
                item.set_model(newdpw)

    def _on_conduit_progress(self, cond, percent, UIDs):
        self.progressText.set_property("text","%2.1d%% complete" % int(percent*100.0))

    def _get_connector_coordinates(self, fromdp, todp):
        """
        Calculates the points a connector shall connect to between fromdp and todp
        @returns: fromx,fromy,tox,toy
        """
        fromx = fromdp.get_right()
        fromy = fromdp.get_top() + (fromdp.get_height()/2) - self.get_top()
        tox = todp.get_left()
        toy = todp.get_top() + (todp.get_height()/2) - self.get_top()
        return fromx,fromy,tox,toy

    def _remove_overlap(self):
        items = self.sinkDpItems
        if len(items) > 0:
            #special case where the top one was deleted
            top = items[0].get_top()-self.get_top()-self.SIDE_PADDING-items[0].LINE_WIDTH
            if top != 0.0:
                for item in items:
                    #translate all those below
                    item.translate(0,-top)
                    if self.sourceItem != None:
                            fromx,fromy,tox,toy = self._get_connector_coordinates(self.sourceItem,item)
                            self.connectorItems[item].reconnect(fromx,fromy,tox,toy)
            else:
                for i in xrange(0, len(items)):
                    try:
                        overlap = items[i].get_bottom() - items[i+1].get_top()
                        log.debug("Sink Overlap: %s %s ----> %s" % (overlap,i,i+1))
                        #If there is anything more than the normal padding gap between then
                        #the dp must be translated
                        if overlap < -self.SIDE_PADDING:
                            #translate all those below, and make their connectors work again
                            for item in items[i+1:]:
                                item.translate(0,overlap+self.SIDE_PADDING)
                                if self.sourceItem != None:
                                    fromx,fromy,tox,toy = self._get_connector_coordinates(self.sourceItem,item)
                                    self.connectorItems[item].reconnect(fromx,fromy,tox,toy)
                    except IndexError:
                        break

    def get_styled_item_names(self):
        return "boundingBox","progressText","divider"

    def get_style_properties(self, specifier):
        if specifier == "boundingBox":
            if self.DIVIDER:
                kwargs = {
                    "line_width":0
                }
            else: 
                if self.FLAT_BOX:
                    kwargs = {
                        "line_width":0,
                        "fill_color_rgba":self.get_style_color_int_rgba("base","prelight")
                    }
                else:
                    pattern = cairo.LinearGradient(0, -30, 0, 100)
                    pattern.add_color_stop_rgb(
                                            0,
                                            *self.get_style_color_rgb("dark","selected")
                                            );
                    pattern.add_color_stop_rgb(
                                            0.7,
                                            *self.get_style_color_rgb("mid","selected")
                                            );
                    
                    kwargs = {
                        "line_width":2.0, 
                        "fill_pattern":pattern,
                        "stroke_color_rgba":self.get_style_color_int_rgba("text","normal")
                    }

        elif specifier == "progressText":
            kwargs = {
                "font":"Sans 7",
                "fill_color_rgba":self.get_style_color_int_rgba("text","normal")
            }
        elif specifier == "divider":
            kwargs = {
                "line_width":3.0,
                "line_cap":cairo.LINE_CAP_ROUND,
                "stroke_color_rgba":self.get_style_color_int_rgba("text_aa","normal")
            }
        else:
            kwargs = {}

        return kwargs

    def update_appearance(self):
        self._resize_height()
    
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

        #add a connector. If we just added a source then we need to make all the
        #connectors, otherwise we just need to add a connector for the new item
        if dpx == 0:
            #make all the connectors
            for s in self.sinkDpItems:
                fromx,fromy,tox,toy = self._get_connector_coordinates(self.sourceItem,s)
                c = ConnectorCanvasItem(self,
                    fromx,
                    fromy,
                    tox,
                    toy,
                    self.model.is_two_way(),
                    conduit.GLOBALS.typeConverter.conversion_exists(
                                        self.sourceItem.model.get_output_type(),
                                        s.model.get_input_type()
                                        )
                    )
                self.connectorItems[s] = c
        else:
            #just make the new connector
            if self.sourceItem != None:
                fromx,fromy,tox,toy = self._get_connector_coordinates(self.sourceItem,item)
                c = ConnectorCanvasItem(self,
                    fromx,
                    fromy,
                    tox,
                    toy,
                    self.model.is_two_way(),
                    conduit.GLOBALS.typeConverter.conversion_exists(
                                        self.sourceItem.model.get_output_type(),
                                        item.model.get_input_type()
                                        )
                    )
                self.connectorItems[item] = c

        self._add_progress_text()
        self.update_appearance()

    def delete_dataprovider_canvas_item(self, item):
        """
        Removes the DataProviderCanvasItem and its connectors
        """
        idx = self.find_child(item)
        if idx != -1:
            self.remove_child(idx)
        else:
            log.warn("Could not find child dataprovider item")

        if item == self.sourceItem:
            self.sourceItem = None
            #remove all connectors (copy because we modify in place)   
            for item in self.connectorItems.copy():
                self._delete_connector(item)
        else:
            self.sinkDpItems.remove(item)
            self._delete_connector(item)

        self._remove_overlap()
        self.update_appearance()

    def set_height(self, h):
        self.boundingBox.set_property("height",h)

        if self.DIVIDER:
            #update height points for the divider line
            self.dividerPoints[0] = (self.dividerPoints[0][0],h+10)
            self.dividerPoints[1] = (self.dividerPoints[0][0],h+10)
            self.divider.set_property("points", 
                                goocanvas.Points(self.dividerPoints))        

    def set_width(self, w):
        true_width = w-self.LINE_WIDTH
        self.boundingBox.set_property("width",true_width)

        if self.DIVIDER:
            #update width points for the divider line
            self.dividerPoints[0] = (true_width*0.33,self.dividerPoints[0][1])
            self.dividerPoints[1] = (2*(true_width*0.33),self.dividerPoints[1][1])
            self.divider.set_property("points", 
                                goocanvas.Points(self.dividerPoints))

        #resize the spacer
        p = goocanvas.Points([(0.0, 0.0), (true_width, 0.0)])
        self.l.set_property("points",p)

        for d in self.sinkDpItems:
            desired = w - d.get_width() - self.SIDE_PADDING
            actual = d.get_left()
            change = desired-actual
            #move righthand dp
            d.translate(change, 0)
            #resize arrow (if exists)
            if self.sourceItem != None:
                self.connectorItems[d].resize_connector_width(change)
                
class ConnectorCanvasItem(_CanvasItem):

    CONNECTOR_RADIUS = 30
    CONNECTOR_YOFFSET = 20
    CONNECTOR_TEXT_XPADDING = 5
    CONNECTOR_TEXT_YPADDING = 10
    LINE_WIDTH = 5.0

    def __init__(self, parent, fromX, fromY, toX, toY, twoway, conversionExists):
        _CanvasItem.__init__(self, parent, None)
    
        self.fromX = fromX
        self.fromY = fromY
        self.toX = toX
        self.toY = toY
        self.twoway = twoway

        self._build_widget()
        
    def _build_widget(self):
        self.left_end_round = goocanvas.Ellipse(
                                    center_x=self.fromX, 
                                    center_y=self.fromY, 
                                    radius_x=6, 
                                    radius_y=6, 
                                    line_width=0.0,
                                    **self.get_style_properties("left_end_round")
                                    )
        points = goocanvas.Points([(self.fromX-6, self.fromY), (self.fromX-7, self.fromY)])
        self.left_end_arrow = goocanvas.Polyline(
                            points=points,
                            line_width=5,
                            end_arrow=True,
                            arrow_tip_length=3,
                            arrow_length=3,
                            arrow_width=3,
                            **self.get_style_properties("left_end_arrow")
                            )

        

        points = goocanvas.Points([(self.toX-1, self.toY), (self.toX, self.toY)])
        self.right_end = goocanvas.Polyline(
                            points=points,
                            line_width=5,
                            end_arrow=True,
                            arrow_tip_length=3,
                            arrow_length=3,
                            arrow_width=3,
                            **self.get_style_properties("right_end")
                            )

        self._draw_arrow_ends()
        self.add_child(self.right_end,-1)

        self.path = goocanvas.Path(
                            data="",
                            line_width=self.LINE_WIDTH,
                            **self.get_style_properties("path")
                            )
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
        self.path = goocanvas.Path(
                            data=p,
                            line_width=self.LINE_WIDTH,
                            **self.get_style_properties("path")
                            )
        self.add_child(self.path,-1)
    
    def get_styled_item_names(self):
        return "left_end_round", "left_end_arrow", "right_end", "path"
        
    def get_style_properties(self, specifier):
        if specifier == "left_end_round":
            kwargs = {
                "fill_color_rgba":self.get_style_color_int_rgba("text","normal")
            }
        elif specifier in ("left_end_arrow", "right_end", "path"):
            kwargs = {
                "stroke_color_rgba":self.get_style_color_int_rgba("text","normal")
            }
        else:
            kwargs = {}
        
        return kwargs
            
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

    def reconnect(self, fromX, fromY, toX, toY):
        self.fromX = fromX
        self.fromY = fromY
        self.toX = toX
        self.toY = toY
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


