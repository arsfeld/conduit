"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""

import os.path
import gobject
import gtk, gtk.gdk

import conduit
from conduit import log,logd,logw

#ENUM represeting the images drawn by ArrowCellRenderer
RIGHT_ARROW = 0
CROSS = 1
LEFT_ARROW = 2
DOUBLE_ARROW = 3
NO_ARROW = 4

#ENUM of directions when resolving a conflict
CONFLICT_COPY_SOURCE_TO_SINK = RIGHT_ARROW  #right drawn arrow
CONFLICT_SKIP = CROSS                       #dont draw an arrow - draw a -x-
CONFLICT_COPY_SINK_TO_SOURCE = LEFT_ARROW   #left drawn arrow
CONFLICT_BOTH = DOUBLE_ARROW                #double headed arrow

#Indexes into the conflict tree model in which 
#conflict data is stored
SOURCE_IDX = 0              #The datasource
SOURCE_DATA_IDX = 1         #The datasource data
SINK_IDX = 2                #The datasink
SINK_DATA_IDX = 3           #The datasink data
DIRECTION_IDX = 4           #The current user decision re: the conflict (-->, <-- or -x-)
AVAILABLE_DIRECTIONS_IDX= 5 #Available user decisions, i.e. in the case of missing
                            #the availabe choices are --> or -x- NOT <--

class ConflictResolver:
    """
    Manages a gtk.TreeView which is used for asking the user what they  
    wish to do in the case of a conflict, or when an item is missing
    """
    def __init__(self, widgets):
        self.model = gtk.TreeStore( gobject.TYPE_PYOBJECT,  #Datasource
                                    gobject.TYPE_PYOBJECT,  #Source Data
                                    gobject.TYPE_PYOBJECT,  #Datasink
                                    gobject.TYPE_PYOBJECT,  #Sink Data
                                    gobject.TYPE_INT,       #Resolved direction
                                    gobject.TYPE_PYOBJECT   #Tuple of valid states for direction 
                                    )
        #In the conflict treeview, group by sink <-> source partnership 
        self.partnerships = {}
        self.numConflicts = 0

        self.view = gtk.TreeView( self.model )
        self.view.set_property("enable-search", False)
        self._build_view()

        #Connect up the GUI
        #this is the scrolled window in the bottom of the main gui
        self.expander = widgets.get_widget("conflictExpander")
        self.expander.connect("activate", self.on_expand)
        self.expander.set_sensitive(False)
        self.fullscreenButton = widgets.get_widget("conflictFullscreenButton")
        self.fullscreenButton.connect("toggled", self.on_fullscreen_toggled)
        self.conflictScrolledWindow = widgets.get_widget("conflictExpanderVBox")
        widgets.get_widget("conflictScrolledWindow").add(self.view)
        #this is a stand alone window for showing conflicts in an easier manner
        self.standalone = gtk.Window()
        self.standalone.set_title("Conflicts")
        self.standalone.set_transient_for(widgets.get_widget("MainWindow"))
        self.standalone.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.standalone.set_destroy_with_parent(True)
        self.standalone.set_default_size(-1, 200)
        self.standalone.add(self.conflictScrolledWindow)
        self.standalone.connect("delete-event", self.on_standalone_closed)
        #the button callbacks are shared
        widgets.get_widget("conflictCancelButton").connect("clicked", self.on_cancel_conflicts)
        

    def _build_view(self):
        #Visible column0 is 
        #[pixbuf + source display name] or 
        #[source_data.get_snippet()]
        column0 = gtk.TreeViewColumn("Source")

        sourceIconRenderer = gtk.CellRendererPixbuf()
        sourceNameRenderer = gtk.CellRendererText()
        column0.pack_start(sourceIconRenderer, False)
        column0.pack_start(sourceNameRenderer, True)

        column0.set_property("expand", True)
        column0.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        column0.set_cell_data_func(sourceNameRenderer, self._name_data_func, True)
        column0.set_cell_data_func(sourceIconRenderer, self._icon_data_func, True)

        #Visible column1 is the arrow to decide the direction
        confRenderer = ConflictCellRenderer()
        column1 = gtk.TreeViewColumn("Resolution", confRenderer)
        column1.set_cell_data_func(confRenderer, self._direction_data_func, DIRECTION_IDX)
        column1.set_property("expand", False)
        column1.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        column1.set_min_width(40)

        #Visible column2 is the display name of source and source data
        column2 = gtk.TreeViewColumn("Sink")

        sinkIconRenderer = gtk.CellRendererPixbuf()
        sinkNameRenderer = gtk.CellRendererText()
        column2.pack_start(sinkIconRenderer, False)
        column2.pack_start(sinkNameRenderer, True)

        column2.set_property("expand", True)
        column2.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        column2.set_cell_data_func(sinkNameRenderer, self._name_data_func, False)
        column2.set_cell_data_func(sinkIconRenderer, self._icon_data_func, False)

        for c in [column0,column1,column2]:
            self.view.append_column( c )

    def _name_data_func(self, column, cell_renderer, tree_model, rowref, is_source):
        """
        The format for displaying the data is
        uri (modified)
        snippet
        """
        #render the headers different to the data
        if tree_model.iter_depth(rowref) == 0:
            if is_source:
                text = tree_model.get_value(rowref, SOURCE_IDX).name
            else:
                text = tree_model.get_value(rowref, SINK_IDX).name
        else:
            if is_source:
                text = tree_model.get_value(rowref, SOURCE_DATA_IDX).get_snippet()
            else:
                text = tree_model.get_value(rowref, SOURCE_DATA_IDX).get_snippet()

        cell_renderer.set_property("text", text)

    def _icon_data_func(self, column, cell_renderer, tree_model, rowref, is_source):
        #Only the headers have icons
        if tree_model.iter_depth(rowref) == 0:
            if is_source:
                icon = tree_model.get_value(rowref, SOURCE_IDX).get_icon()
            else:
                icon = tree_model.get_value(rowref, SINK_IDX).get_icon()
        else:
            icon = None

        cell_renderer.set_property("pixbuf", icon)

    def _direction_data_func(self, column, cell_renderer, tree_model, rowref, user_data):
        direction = tree_model.get_value(rowref, user_data)
        if tree_model.iter_depth(rowref) == 0:
            cell_renderer.set_property('visible', False)
            cell_renderer.set_property('mode', gtk.CELL_RENDERER_MODE_INERT)
        else:
            cell_renderer.set_property('visible', True)
            cell_renderer.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)
            cell_renderer.set_direction(direction)

    def _set_conflict_titles(self):
        self.expander.set_label("Conflicts (%s)" % self.numConflicts)
        self.standalone.set_title("Conflicts (%s)" % self.numConflicts)

    def on_conflict(self, thread, source, sourceData, sink, sinkData, validChoices):
        #We start with the expander disabled. Make sure we only enable it once
        if len(self.model) == 0:
            self.expander.set_sensitive(True)

        self.numConflicts += 1
        rowdata = ( source, sourceData, sink, sinkData, CONFLICT_SKIP, validChoices)
        if (source,sink) in self.partnerships:
            self.model.append(self.partnerships[(source,sink)], rowdata)  
        else:
            self.partnerships[(source,sink)] = self.model.append(None, rowdata)

        #update the expander label and the standalone window title
        self._set_conflict_titles()

    def on_expand(self, sender):
        pass

    def on_fullscreen_toggled(self, sender):
        #switches between showing the conflicts in a standalone window.
        #uses fullscreenButton.get_active() as a state variable
        if self.fullscreenButton.get_active():
            self.expander.set_expanded(False)
            self.fullscreenButton.set_image(gtk.image_new_from_icon_name("gtk-leave-fullscreen", gtk.ICON_SIZE_MENU))
            self.conflictScrolledWindow.reparent(self.standalone)
            self.standalone.show()
            self.expander.set_sensitive(False)
        else:
            self.fullscreenButton.set_image(gtk.image_new_from_icon_name("gtk-fullscreen", gtk.ICON_SIZE_MENU))
            self.conflictScrolledWindow.reparent(self.expander)
            self.standalone.hide()
            self.expander.set_sensitive(True)

    def on_standalone_closed(self, sender, event):
        self.fullscreenButton.set_active(False)
        self.on_fullscreen_toggled(sender)
        return True

    #Connect to OK button
    def on_resolve_conflicts(self, sender):
        pass
    
    #Connect to cancel button
    def on_cancel_conflicts(self, sender):
        self.model.clear()
        self.partnerships = {}
        self.numConflicts = 0
        self._set_conflict_titles()
        pass

class ConflictCellRenderer(gtk.GenericCellRenderer):

    LEFT_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-left.png"))
    RIGHT_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-right.png"))
    SKIP_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-skip.png"))

    def __init__(self):
        gtk.GenericCellRenderer.__init__(self)
        self.image = None

    def on_get_size(self, widget, cell_area):
        return  (   0,0, 
                    ConflictCellRenderer.SKIP_IMAGE.get_property("width"), 
                    ConflictCellRenderer.SKIP_IMAGE.get_property("height")
                    )

    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
        if self.image != None:
            self.image.render_to_drawable_alpha(window,
                                            0, 0,                       #x, y in pixbuf
                                            cell_area.x, cell_area.y,   # x, y in drawable
                                            -1, -1,                     # use pixbuf width & height
                                            0, 0,                       # alpha (deprecated params)
                                            gtk.gdk.RGB_DITHER_NONE,
                                            0, 0
                                            )
        return True

    def set_direction(self, direction):
        if direction == CONFLICT_COPY_SINK_TO_SOURCE:
            self.image = ConflictCellRenderer.LEFT_IMAGE
        elif direction == CONFLICT_COPY_SOURCE_TO_SINK:
            self.image = ConflictCellRenderer.RIGHT_IMAGE
        elif direction == CONFLICT_SKIP:
            self.image = ConflictCellRenderer.SKIP_IMAGE
        else:
            self.image = None

    def on_activate(self, event, widget, path, background_area, cell_area, flags):
        model = widget.get_model()
        #Click toggles between --> and <-- and -x- but only within the list
        #of valid choices
        if model[path][DIRECTION_IDX] == model[path][AVAILABLE_DIRECTIONS_IDX][-1]:
            model[path][DIRECTION_IDX] = model[path][AVAILABLE_DIRECTIONS_IDX][0]
        else:
            model[path][DIRECTION_IDX] += 1

        return True


