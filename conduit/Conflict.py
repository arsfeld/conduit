"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""

import os.path
import gobject
import gtk, gtk.gdk

import conduit

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
SOURCE_NAME_IDX = 1         #The datasource name
SOURCE_DATA_IDX = 2         #The datasource data
SINK_IDX = 3                #The datasink
SINK_NAME_IDX = 4           #The datasink name
SINK_DATA_IDX = 5           #The datasink data
DIRECTION_IDX = 6           #The current user decision re: the conflict (-->, <-- or -x-)
AVAILABLE_DIRECTIONS_IDX= 7 #Available user decisions, i.e. in the case of missing
                            #the availabe choices are --> or -x- NOT <--

class ConflictResolver:
    """
    Manages a gtk.TreeView which is used for asking the user what they  
    wish to do in the case of a conflict, or when an item is missing
    """
    def __init__(self):
        self.model = gtk.TreeStore( gobject.TYPE_PYOBJECT,  #Datasource
                                    gobject.TYPE_STRING,    #Source Name
                                    gobject.TYPE_PYOBJECT,  #Source Data
                                    gobject.TYPE_PYOBJECT,  #Datasink
                                    gobject.TYPE_STRING,    #Sink Name
                                    gobject.TYPE_PYOBJECT,  #Sink Data
                                    gobject.TYPE_INT,       #Resolved direction
                                    gobject.TYPE_PYOBJECT   #Tuple of valid states for direction 
                                    )

        #FIXME: Fill with test data. Can Remove at some stage...
        #self._test_data()

        self.view = gtk.TreeView( self.model )
        self.view.set_property("enable-search", False)
        self._build_view()

    def _test_data(self):
        for i in range(0,3):
            s = str(i)
            self.model.append(  None,   (
                                        None,
                                        "Source"+s,
                                        i,
                                        None,
                                        "Sink"+s,
                                        i,
                                        i,
                                        (0,1,2,3)
                                        )
                                )

    def _build_view(self):
        #Visible column0 is the name of the datasource
        column0 = gtk.TreeViewColumn("Source Name", gtk.CellRendererText(), text=SOURCE_NAME_IDX)
        column0.set_property("expand", True)
        column0.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

        #Visible column1 is the arrow to decide the direction
        confRenderer = ConflictCellRenderer()
        column1 = gtk.TreeViewColumn("Resolution", confRenderer)
        column1.set_cell_data_func(confRenderer, self.set_direction_func, DIRECTION_IDX)
        column1.set_property("expand", False)
        column1.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        column1.set_min_width(40)

        #Visible column2 is the name of the datasource
        column2 = gtk.TreeViewColumn("Sink Name", gtk.CellRendererText(), text=SINK_NAME_IDX)
        column2.set_property("expand", True)
        column2.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

        for c in [column0,column1,column2]:
            self.view.append_column( c )

    def set_direction_func(self, column, cell_renderer, tree_model, iter, user_data):
        direction = tree_model.get_value(iter, user_data)
        cell_renderer.set_direction(direction)

    def on_conflict(self, thread, source, sourceData, sink, sinkData, validChoices):
        sourceName = source.name
        sinkName = sink.name
        self.model.append(  None, ( 
                                    source,
                                    sourceName,
                                    sourceData,
                                    sink,
                                    sinkName,
                                    sinkData,
                                    validChoices[0],
                                    validChoices)
                            )

    #Connect to OK button
    def on_resolve_conflicts(self, sender):
        pass
    
    #Connect to cancel button
    def on_cancel_conflicts(self, sender):
        pass

class ConflictCellRenderer(gtk.GenericCellRenderer):

    LEFT_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-left.png"))
    RIGHT_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-right.png"))
    BOTH_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-twoway.png"))
    SKIP_IMAGE = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(conduit.SHARED_DATA_DIR, "conflict-skip.png"))

    def __init__(self):
        gtk.GenericCellRenderer.__init__(self)
        self.set_property('visible', True)
        self.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)
        self.image = None

    def on_get_size(self, widget, cell_area):
        return  (   0,0, 
                    ConflictCellRenderer.BOTH_IMAGE.get_property("width"), 
                    ConflictCellRenderer.BOTH_IMAGE.get_property("height")
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
        elif direction == CONFLICT_BOTH:
            self.image = ConflictCellRenderer.BOTH_IMAGE
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

        return False


