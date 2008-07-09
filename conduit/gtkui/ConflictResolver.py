"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""
import traceback
import time
import gobject
import gtk, gtk.gdk
import pango
import logging
log = logging.getLogger("gtkui.ConflictResolver")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Vfs as Vfs
import conduit.Conflict as Conflict

from gettext import gettext as _

#Indexes into the conflict tree model in which conflict data is stored
CONFLICT_IDX = 0            #The conflict object
DIRECTION_IDX = 1           #The current user decision re: the conflict (-->, <-- or -x-)

class ConflictHeader:
    def __init__(self, sourceWrapper, sinkWrapper):
        self.sourceWrapper = sourceWrapper
        self.sinkWrapper = sinkWrapper

    def get_snippet(self, is_source):
        if is_source:
            return self.sourceWrapper.name
        else:
            return self.sinkWrapper.name

    def get_icon(self, is_source):
        if is_source:
            return self.sourceWrapper.get_icon()
        else:
            return self.sinkWrapper.get_icon()

class ConflictResolver:
    """
    Manages a gtk.TreeView which is used for asking the user what they  
    wish to do in the case of a conflict
    """
    def __init__(self, widgets):
        self.model = gtk.TreeStore( gobject.TYPE_PYOBJECT,  #Conflict
                                    gobject.TYPE_INT        #Resolved direction
                                    )
        #In the conflict treeview, group by sink <-> source partnership 
        self.partnerships = {}
        self.numConflicts = 0

        self.view = gtk.TreeView( self.model )
        self._build_view()

        #Connect up the GUI
        #this is the scrolled window in the bottom of the main gui
        self.expander = widgets.get_widget("conflictExpander")
        self.expander.connect("activate", self.on_expand)
        self.vpane = widgets.get_widget("vpaned1")
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
        #widgets cannot have two parents       
        #self.standalone.add(self.conflictScrolledWindow)
        self.standalone.connect("delete-event", self.on_standalone_closed)
        #the button callbacks are shared
        widgets.get_widget("conflictCancelButton").connect("clicked", self.on_cancel_conflicts)
        widgets.get_widget("conflictResolveButton").connect("clicked", self.on_resolve_conflicts)
        #the state of the compare button is managed by the selection changed callback
        self.compareButton = widgets.get_widget("conflictCompareButton")
        self.compareButton.connect("clicked", self.on_compare_conflicts)
        self.compareButton.set_sensitive(False)

    def _build_view(self):
        #Visible column0 is 
        #[pixbuf + source display name] or 
        #[source_data.get_snippet()]
        column0 = gtk.TreeViewColumn(_("Source"))

        sourceIconRenderer = gtk.CellRendererPixbuf()
        sourceNameRenderer = gtk.CellRendererText()
        sourceNameRenderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column0.pack_start(sourceIconRenderer, False)
        column0.pack_start(sourceNameRenderer, True)

        column0.set_property("expand", True)
        column0.set_cell_data_func(sourceNameRenderer, self._name_data_func, True)
        column0.set_cell_data_func(sourceIconRenderer, self._icon_data_func, True)

        #Visible column1 is the arrow to decide the direction
        confRenderer = ConflictCellRenderer()
        column1 = gtk.TreeViewColumn(_("Resolution"), confRenderer)
        column1.set_cell_data_func(confRenderer, self._direction_data_func, DIRECTION_IDX)
        column1.set_property("expand", False)

        #Visible column2 is the display name of source and source data
        column2 = gtk.TreeViewColumn(_("Sink"))

        sinkIconRenderer = gtk.CellRendererPixbuf()
        sinkNameRenderer = gtk.CellRendererText()
        sinkNameRenderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column2.pack_start(sinkIconRenderer, False)
        column2.pack_start(sinkNameRenderer, True)

        column2.set_property("expand", True)
        column2.set_cell_data_func(sinkNameRenderer, self._name_data_func, False)
        column2.set_cell_data_func(sinkIconRenderer, self._icon_data_func, False)

        for c in [column0,column1,column2]:
            self.view.append_column( c )

        #set view properties
        self.view.set_property("enable-search", False)
        self.view.get_selection().connect("changed", self.on_selection_changed)

    def _name_data_func(self, column, cell_renderer, tree_model, rowref, is_source):
        conflict = tree_model.get_value(rowref, CONFLICT_IDX)
        text = conflict.get_snippet(is_source)
        cell_renderer.set_property("text", text)

    def _icon_data_func(self, column, cell_renderer, tree_model, rowref, is_source):
        conflict = tree_model.get_value(rowref, CONFLICT_IDX)
        icon = conflict.get_icon(is_source)
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
        self.expander.set_label(_("Conflicts (%s)") % self.numConflicts)
        self.standalone.set_title(_("Conflicts (%s)") % self.numConflicts)

    def on_conflict(self, cond, conflict):
        #We start with the expander disabled. Make sure we only enable it once
        if len(self.model) == 0:
            self.expander.set_sensitive(True)

        self.numConflicts += 1
        source,sink = conflict.get_partnership()
        if (source,sink) not in self.partnerships:
            #create a header row
            header = ConflictHeader(source, sink)
            rowref = self.model.append(None, (header, Conflict.CONFLICT_ASK))
            self.partnerships[(source,sink)] = (rowref,conflict)

        rowref = self.partnerships[(source,sink)][0]
        self.model.append(rowref, (conflict, Conflict.CONFLICT_ASK))

        #FIXME: Do this properly with model signals and a count function
        #update the expander label and the standalone window title
        #self._set_conflict_titles()

    def on_expand(self, sender):
        #Force the vpane to move to the bottom
        self.vpane.set_position(-1)

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

    def on_resolve_conflicts(self, sender):
        #save the resolved rowrefs and remove them at the end
        resolved = []

        def _resolve_func(model, path, rowref):
            #skip header rows
            if model.iter_depth(rowref) == 0:
                return

            direction = model[path][DIRECTION_IDX]
            conflict = model[path][CONFLICT_IDX]

            if conflict.resolve(direction):
                resolved.append(rowref)

        self.model.foreach(_resolve_func)
        for r in resolved:
            self.model.remove(r)

        #now look for any sync partnerships with no children
        empty = []
        for source,sink in self.partnerships:
            rowref = self.partnerships[(source,sink)][0]
            numChildren = self.model.iter_n_children(rowref)
            if numChildren == 0:
                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
                empty.append( (rowref, source, sink) )
            else:
                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_CONFLICT)

        #do in two loops so as to not change the model while iterating
        for rowref, source, sink in empty:
            self.model.remove(rowref)
            try:
                del(self.partnerships[(source,sink)])
            except KeyError: pass

    def on_cancel_conflicts(self, sender):
        self.model.clear()
        self.partnerships = {}
        self.numConflicts = 0
        self._set_conflict_titles()

    def on_compare_conflicts(self, sender):
        model, rowref = self.view.get_selection().get_selected()
        conflict = model.get_value(rowref, CONFLICT_IDX)
        Vfs.uri_open(conflict.sourceData.get_open_URI())
        Vfs.uri_open(conflict.sinkData.get_open_URI())

    def on_selection_changed(self, treeSelection):
        """
        Makes the compare button active only if an open_URI for the data
        has been set and its not a header row.
        FIXME: In future could convert to text to allow user to compare that way
        """
        model, rowref = treeSelection.get_selected()
        #when the rowref under the selected row is removed by resolve thread
        if rowref == None:
            self.compareButton.set_sensitive(False)
        else:
            conflict = model.get_value(rowref, CONFLICT_IDX)
            if model.iter_depth(rowref) == 0:
                self.compareButton.set_sensitive(False)
            #both must have an open_URI set to work
            elif conflict.sourceData.get_open_URI() != None and conflict.sinkData.get_open_URI() != None:
                self.compareButton.set_sensitive(True)
            else:
                self.compareButton.set_sensitive(False)

class ConflictCellRenderer(gtk.GenericCellRenderer):
    """
    An unfortunately neccessary wrapper around a CellRenderPixbuf because
    said renderer is not activatable
    """
    def __init__(self):
        gtk.GenericCellRenderer.__init__(self)
        self.image = None

    def on_get_size(self, widget, cell_area):
        return  (   0,0, 
                    16,16
                    )

    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
        if self.image != None:
            middle_x = (cell_area.width - 16) / 2
            middle_y = (cell_area.height - 16) / 2  
            self.image.render_to_drawable_alpha(window,
                                            0, 0,                       #x, y in pixbuf
                                            middle_x + cell_area.x,     #middle x in drawable
                                            middle_y + cell_area.y,     #middle y in drawable
                                            -1, -1,                     # use pixbuf width & height
                                            0, 0,                       # alpha (deprecated params)
                                            gtk.gdk.RGB_DITHER_NONE,
                                            0, 0
                                            )
#            self.image.draw_pixbuf(
#                            None,       #gc for clipping
#                            window,     #draw to
#                            0, 0,                       #x, y in pixbuf
#                            cell_area.x, cell_area.y,   # x, y in drawable
#                            -1, -1,                     # use pixbuf width & height
#                            gtk.gdk.RGB_DITHER_NONE,
#                            0, 0
#                            )
        return True

    def set_direction(self, direction):
        if direction == Conflict.CONFLICT_COPY_SINK_TO_SOURCE:
            self.image = gtk.icon_theme_get_default().load_icon("conduit-conflict-left",16,0)
        elif direction == Conflict.CONFLICT_COPY_SOURCE_TO_SINK:
            self.image = gtk.icon_theme_get_default().load_icon("conduit-conflict-right",16,0)
        elif direction == Conflict.CONFLICT_SKIP:
            self.image = gtk.icon_theme_get_default().load_icon("conduit-conflict-skip",16,0)
        elif direction == Conflict.CONFLICT_DELETE:
            self.image = gtk.icon_theme_get_default().load_icon("conduit-conflict-delete",16,0)
        elif direction == Conflict.CONFLICT_ASK:
            self.image = gtk.icon_theme_get_default().load_icon("conduit-conflict-ask",16,0)
        else:
            self.image = None

    def on_activate(self, event, widget, path, background_area, cell_area, flags):
        model = widget.get_model()
        conflict = model[path][CONFLICT_IDX]
        #Click toggles between --> and <-- and -x- but only within the list
        #of valid choices. If at the end of the valid choices, then loop around
        try:
            curIdx = list(conflict.choices).index(model[path][DIRECTION_IDX])
        except ValueError:
            #Because CONFLICT_ASK is never a valid choice, its just the default
            #to make the user have to acknowledge the conflict
            curIdx = 0

        if curIdx == len(conflict.choices) - 1:
            model[path][DIRECTION_IDX] = conflict.choices[0]
        else:
            model[path][DIRECTION_IDX] = conflict.choices[curIdx+1]

        return True
