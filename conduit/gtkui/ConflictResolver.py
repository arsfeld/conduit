"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""
import traceback
import threading
import time
import gobject
import gtk, gtk.gdk
import pango
import logging
log = logging.getLogger("gtkui.ConflictResolver")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Conflict as Conflict

#Indexes into the conflict tree model in which conflict data is stored
CONFLICT_IDX = 0            #The conflict object
DIRECTION_IDX = 1           #The current user decision re: the conflict (-->, <-- or -x-)

class ConflictHeader(Conflict.Conflict):
    def __init__(self, sourceWrapper, sinkWrapper):
        Conflict.Conflict.__init__(self, sourceWrapper, None, sinkWrapper, None, (), False)

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

        #resolve conflicts in a background thread
        self.resolveThreadManager = ConflictResolveThreadManager(3)

        self.view = gtk.TreeView( self.model )
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
        column0 = gtk.TreeViewColumn("Source")

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
        column1 = gtk.TreeViewColumn("Resolution", confRenderer)
        column1.set_cell_data_func(confRenderer, self._direction_data_func, DIRECTION_IDX)
        column1.set_property("expand", False)

        #Visible column2 is the display name of source and source data
        column2 = gtk.TreeViewColumn("Sink")

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
        """
        The format for displaying the data is
        uri (modified)
        snippet
        """
        conflict = tree_model.get_value(rowref, CONFLICT_IDX)
        #render the headers different to the data
        if tree_model.iter_depth(rowref) == 0:
            if is_source:
                text = conflict.sourceWrapper.name
            else:
                text = conflict.sinkWrapper.name
        else:
            if is_source:
                text = conflict.sourceData.get_snippet()
            else:
                text = conflict.sinkData.get_snippet()

        cell_renderer.set_property("text", text)

    def _icon_data_func(self, column, cell_renderer, tree_model, rowref, is_source):
        conflict = tree_model.get_value(rowref, CONFLICT_IDX)
        #Only the headers have icons
        if tree_model.iter_depth(rowref) == 0:
            if is_source:
                icon = conflict.sourceWrapper.get_icon()
            else:
                icon = conflict.sinkWrapper.get_icon()
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

    def _conflict_resolved(self, sender, rowref):
        """
        Callback when a ConflictResolveThread finishes. Deletes the 
        appropriate conflict from the model. Also looks to see if there
        are any other conflicts remainng so it can set the sink status and/or
        delete the partnership
        """
        if not self.model.iter_is_valid(rowref):
            #FIXME: Need to work a way around this before resolution can be threaded
            log.warn("Iters do not persist throug signal emission!")
            return

        self.model.remove(rowref)
        #now look for any sync partnerships with no children
        empty = False
        for source,sink in self.partnerships:
            rowref = self.partnerships[(source,sink)]
            numChildren = self.model.iter_n_children(rowref)
            if numChildren == 0:
                empty = True

        #do in two loops so as to not change the dict while iterating
        if empty:
            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
            del(self.partnerships[(source,sink)])
            self.model.remove(rowref)
        else:
            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_CONFLICT)

        #FIXME: Do this properly with model signals and a count function
        self.numConflicts -= 1
        self._set_conflict_titles()

    def on_conflict(self, thread, conflict):
        #We start with the expander disabled. Make sure we only enable it once
        if len(self.model) == 0:
            self.expander.set_sensitive(True)

        self.numConflicts += 1
        source = conflict.sourceWrapper
        sink = conflict.sinkWrapper
        if (source,sink) not in self.partnerships:
            #create a header row
            header = ConflictHeader(source, sink)
            self.partnerships[(source,sink)] = self.model.append(None, (header, Conflict.CONFLICT_SKIP) )

        self.model.append(self.partnerships[(source,sink)], (conflict, Conflict.CONFLICT_SKIP) )  

        #FIXME: Do this properly with model signals and a count function
        #update the expander label and the standalone window title
        #self._set_conflict_titles()

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

    def on_resolve_conflicts(self, sender):
        """
        According to the users selection, start backgroun threads to
        resolve the conflicts
        """
        IHaveMadeItersPersist = False

        #save the resolved rowrefs and remove them at the end
        resolved = []

        def _resolve_func(model, path, rowref):
            #skip header rows
            if model.iter_depth(rowref) == 0:
                return

            direction = model[path][DIRECTION_IDX]
            conflict = model[path][CONFLICT_IDX]

            #do as the user inducated with the arrow
            if direction == Conflict.CONFLICT_SKIP:
                log.debug("Not resolving")
                return
            elif direction == Conflict.CONFLICT_COPY_SOURCE_TO_SINK:
                log.debug("Resolving source data --> sink")
                data = conflict.sourceData
                source = conflict.sourceWrapper
                sink = conflict.sinkWrapper
            elif direction == Conflict.CONFLICT_COPY_SINK_TO_SOURCE:
                log.debug("Resolving source <-- sink data")
                data = conflict.sinkData
                source = conflict.sinkWrapper
                sink = conflict.sourceWrapper
            elif direction == Conflict.CONFLICT_DELETE:
                log.debug("Resolving deletion  --->")
                data = conflict.sinkData
                source = conflict.sourceWrapper
                sink = conflict.sinkWrapper
            else:
                log.warn("Unknown resolution")

            deleted = conflict.isDeletion

            #add to resolve thread
            #FIXME: Think of a way to make rowrefs persist through signals
            if IHaveMadeItersPersist:
                self.resolveThreadManager.make_thread(self._conflict_resolved,rowref,data,sink,source,deleted)
            else:
                try:
                    if deleted:
                        log.debug("Resolving conflict. Deleting %s from %s" % (data, sink))
                        conduit.Synchronization._delete_data(source, sink, data.get_UID())
                    else:
                        log.debug("Resolving conflict. Putting %s --> %s" % (data, sink))
                        conduit.Synchronization._put_data(source, sink, data, None, True)

                    resolved.append(rowref)
                except Exception:
                    log.warn("Could not resolve conflict\n%s" % traceback.format_exc())

        self.model.foreach(_resolve_func)
        for r in resolved:
            self.model.remove(r)

        if not IHaveMadeItersPersist:
            #now look for any sync partnerships with no children
            empty = []
            for source,sink in self.partnerships:
                rowref = self.partnerships[(source,sink)]
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
        Utils.open_URI(conflict.sourceData.get_open_URI())
        Utils.open_URI(conflict.sinkData.get_open_URI())

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
        else:
            self.image = None

    def on_activate(self, event, widget, path, background_area, cell_area, flags):
        model = widget.get_model()
        #Click toggles between --> and <-- and -x- but only within the list
        #of valid choices
        conflict = model[path][CONFLICT_IDX]
        curIdx = list(conflict.choices).index(model[path][DIRECTION_IDX])

        if curIdx == len(conflict.choices) - 1:
            model[path][DIRECTION_IDX] = conflict.choices[0]
        else:
            model[path][DIRECTION_IDX] = conflict.choices[curIdx+1]

        return True

class _ConflictResolveThread(threading.Thread, gobject.GObject):
    """
    Resolves a conflict or deletion event. If a deleted event then
    calls sink.delete, if a conflict then does put()
    """
    __gsignals__ =  { 
                    "completed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    def __init__(self, *args):
        """
        Args
         - arg[0]: data
         - arg[1]: sink
         - arg[2]: source
         - arg[3]: isDeleted
        """
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        
        self.data = args[0]
        self.sink = args[1]
        self.source = args[2]
        self.isDeleted = args[3]

        self.setName("ResolveThread for sink: %s. (Delete: %s)" % (self.sink, self.isDeleted))

    def emit(self, *args):
        """
        Override the gobject signal emission so that all signals are emitted 
        from the main loop on an idle handler
        """
        gobject.idle_add(gobject.GObject.emit,self,*args)

    def run(self):
        try:
            if self.isDeleted:
                log.debug("Resolving conflict. Deleting %s from %s" % (self.data, self.sink))
                conduit.Synchronization._delete_data(self.source, self.sink, self.data.get_UID())
            else:
                log.debug("Resolving conflict. Putting %s --> %s" % (self.data, self.sink))
                conduit.Synchronization._put_data(self.source, self.sink, self.data, None, True)
        except Exception:                        
            log.warn("Could not resolve conflict\n%s" % traceback.format_exc())
            #sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)

        self.emit("completed")

class ConflictResolveThreadManager:
    """
    Manages many resolve threads. This involves joining and cancelling
    said threads, and respecting a maximum num of concurrent threads limit
    """
    def __init__(self, maxConcurrentThreads):
        self.maxConcurrentThreads = maxConcurrentThreads
        #stores all threads, running or stopped
        self.fooThreads = {}
        #the pending thread args are used as an index for the stopped threads
        self.pendingFooThreadArgs = []

    def _register_thread_completed(self, thread, *args):
        """
        Decrements the count of concurrent threads and starts any 
        pending threads if there is space
        """
        del(self.fooThreads[args])
        running = len(self.fooThreads) - len(self.pendingFooThreadArgs)

        log.debug("Thread %s completed. %s running, %s pending" % (
                            thread, running, len(self.pendingFooThreadArgs)))

        if running < self.maxConcurrentThreads:
            try:
                args = self.pendingFooThreadArgs.pop()
                log.debug("Starting pending %s" % self.fooThreads[args])
                self.fooThreads[args].start()
            except IndexError: pass

    def make_thread(self, completedCb, completedCbUserData,  *args):
        """
        Makes a thread with args. The thread will be started when there is
        a free slot
        """
        running = len(self.fooThreads) - len(self.pendingFooThreadArgs)

        if args not in self.fooThreads:
            thread = _ConflictResolveThread(*args)
            #signals run in the order connected. Connect the user one first 
            #incase they wish to do something before we delete the thread
            thread.connect("completed", completedCb, completedCbUserData)
            thread.connect("completed", self._register_thread_completed, *args)
            #This is why we use args, not kwargs, because args are hashable
            self.fooThreads[args] = thread

            if running < self.maxConcurrentThreads:
                log.debug("Starting %s" % thread)
                self.fooThreads[args].start()
            else:
                log.debug("Queing %s" % thread)
                self.pendingFooThreadArgs.append(args)
        else:
            log.debug("Already resolving conflict")

    def join_all_threads(self):
        """
        Joins all threads (blocks)

        Unfortunately we join all the threads do it in a loop to account
        for join() a non started thread failing. To compensate I time.sleep()
        to not smoke CPU
        """
        joinedThreads = 0
        while(joinedThreads < len(self.fooThreads)):
            for thread in self.fooThreads.values():
                try:
                    thread.join()
                    joinedThreads += 1
                except AssertionError: 
                    #deal with not started threads
                    time.sleep(1)
