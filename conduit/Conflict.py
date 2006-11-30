"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""

import os.path
import gobject
import gtk, gtk.gdk

import conduit

#ENUM of directions when resolving a conflict
CONFLICT_SOURCE_TO_SINK = 0     #left drawn arrow
CONFLICT_SINK_TO_SOURCE = 1     #right drawn arrow
CONFLICT_SKIP = 2               #dont draw an arrow
CONFLICT_BOTH = 3               #double headed arrow

#Indexes into the conflict model in which conflict data is stored
SOURCE_NAME_IDX = 0
SOURCE_DATA_IDX_IDX = 1
SINK_NAME_IDX = 2
SOURCE_DATA_IDX_IDX = 3
DIRECTION_IDX = 4

class ConflictResolver:

    def __init__(self):
        self.model = gtk.TreeStore( gobject.TYPE_STRING,    #Source Name
                                    gobject.TYPE_INT,       #Source Data Index
                                    gobject.TYPE_STRING,    #Sink Name
                                    gobject.TYPE_INT,       #Sink Data Index
                                    gobject.TYPE_INT        #Resolved direction
                                    )

        #FIXME: Fill with test data. Can Remove at some stage...
        self._test_data()

        self.view = gtk.TreeView( self.model )
        self._build_view()

    def _test_data(self):
        for i in range(0,3):
            s = str(i)
            self.model.append(None, ("Source"+s,i,"Sink"+s,i,i))

    def _build_view(self):
        #Visible column0 is the name of the datasource
        column0 = gtk.TreeViewColumn("Source Name", gtk.CellRendererText(), text=SOURCE_NAME_IDX)

        #Visible column1 is the arrow to decide the direction
        confRenderer = ConflictCellRenderer()
        column1 = gtk.TreeViewColumn("Conflict", confRenderer)
        column1.set_cell_data_func(confRenderer, self.set_direction_func, DIRECTION_IDX)

        #Visible column2 is the name of the datasource
        column2 = gtk.TreeViewColumn("Sink Name", gtk.CellRendererText(), text=SINK_NAME_IDX)

        self.view.append_column( column0 )
        self.view.append_column( column1 )
        self.view.append_column( column2 )

    def set_direction_func(self, column, cell_renderer, tree_model, iter, user_data):
        direction = tree_model.get_value(iter, user_data)
        cell_renderer.set_direction(direction)

    #Callback from syncmanager
    def on_conflict(self, sender):
        pass

    #Connect to OK button
    def on_resolve_conflicts(self, sender):
        pass
    
    #Connect to cancel button
    def on_cancel_conflicts(self, sender):
        pass

class ArrowCellRenderer(gtk.GenericCellRenderer):

    LEFT_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "one-way-left.png"))
    RIGHT_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "one-way-right.png"))
    BOTH_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "two-way.png"))
    SKIP_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "skip.png"))

    def __init__(self):
        gtk.GenericCellRenderer.__init__(self)
        self.set_property('visible', True)
        self.image = None

    def on_get_size(self, widget, cell_area):
        return  (   0,0, 
                    ArrowCellRenderer.BOTH_IMAGE.get_property("width"), 
                    ArrowCellRenderer.BOTH_IMAGE.get_property("height")
                    )

    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
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
        if direction == CONFLICT_SOURCE_TO_SINK:
            self.image = ArrowCellRenderer.LEFT_IMAGE
        elif direction == CONFLICT_SINK_TO_SOURCE:
            self.image = ArrowCellRenderer.RIGHT_IMAGE
        elif direction == CONFLICT_SKIP:
            self.image = ArrowCellRenderer.SKIP_IMAGE
        elif direction == CONFLICT_BOTH:
            self.image = ArrowCellRenderer.BOTH_IMAGE
        else:
            print "UNKNOWN DIRECTION"

class ConflictCellRenderer(ArrowCellRenderer):
    def __init__(self):
        ArrowCellRenderer.__init__(self)
        self.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)

    def on_activate(self, event, widget, path, background_area, cell_area, flags):
        model = widget.get_model()
        #Click toggles between --> and <-- and -x-
        if model[path][DIRECTION_IDX] == CONFLICT_SKIP:
            model[path][DIRECTION_IDX] = CONFLICT_SOURCE_TO_SINK
        else:
            model[path][DIRECTION_IDX] += 1

        return False


