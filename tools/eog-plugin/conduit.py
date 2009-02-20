import os
import eog
import gtk
import dbus, dbus.glib

try:
    import libconduit
except ImportError:
    import conduit.libconduit as libconduit

DEBUG = True
ICON_SIZE = 24
SUPPORTED_SINKS = {
    "FlickrTwoWay"      :   "Upload to Flickr",
    "PicasaTwoWay"      :   "Upload to Picasa",
    "SmugMugTwoWay"     :   "Upload to SmugMug",
    "ShutterflySink"    :   "Upload to Shutterfly",
    "BoxDotNetTwoWay"   :   "Upload to Box.net",
    "FacebookSink"      :   "Upload to Facebook",
    "IPodPhotoSink"     :   "Add to iPod"
}
if DEBUG:
    SUPPORTED_SINKS["TestImageSink"] = "Test Image Sink"

class EogConduitWrapper(libconduit.ConduitWrapper):

    CONFIG_PATH='~/.conduit/eog-plugin'

    def add_rowref(self):
        #store the rowref in the store with the icon conduit gave us
        info = self.conduit.SinkGetInformation(dbus_interface=libconduit.EXPORTER_DBUS_IFACE)
        desc = SUPPORTED_SINKS[self.name]
        self._add_rowref(
                name=desc,
                uri="",
                status="ready",
                pixbuf=gtk.gdk.pixbuf_new_from_file_at_size(info['icon_path'], ICON_SIZE, ICON_SIZE)
        )

class ConduitPlugin(eog.Plugin):
    def __init__(self):
        self.debug = DEBUG
        self.conduit = libconduit.ConduitApplicationWrapper(
                                        conduitWrapperKlass=EogConduitWrapper,
                                        addToGui=self.debug,
                                        store=True,
                                        debug=self.debug
                                        )
        self.conduit.connect("conduit-started", self._on_conduit_started)
        self.running = self.conduit.connect_to_conduit(startConduit=True)

        #dictionary holding items that are set sensitive or not when
        #conduit is started/stopped
        self.windows = {}
    
    def _debug(self, msg):
        if self.debug:
            print "EOG: ", msg

    def _on_conduit_started(self, sender, started):
        self._debug("Conduit started: %s" % started)
        self.running = started
        #set (in)sensitive on widgets in all windows
        for box, ui_action_group in self.windows.values():
            box.set_sensitive(self.running)
            ui_action_group.set_sensitive(self.running)

    def _on_upload_clicked(self, sender, window):
        eogImage = window.get_image()
        name = sender.get_property("name")

        if eogImage != None:
            thumb = eogImage.get_thumbnail()
            pb = thumb.scale_simple(ICON_SIZE,ICON_SIZE,gtk.gdk.INTERP_BILINEAR)
            uri = eogImage.get_uri_for_display()

            self.conduit.upload(name, uri, pb)

    def _on_sync_clicked(self, sender, window):
        self.conduit.sync()

    def _on_clear_clicked(self, sender, window):
        self.conduit.clear()

    def _on_row_activated(self, treeview, path, view_column):
        #check the user didnt click a header row
        rowref = treeview.get_model().get_iter(path)
        if treeview.get_model().iter_depth(rowref) == 0:
            return

        #open eog to show the image
        clickedUri = treeview.get_model()[path][2]
        app = eog.eog_application_get_instance()
        app.open_uri_list((clickedUri,))

    def _prepare_ui(self, window):
        #
        #the sidebar is a treeview where photos to upload are grouped by the
        #upload service, with a clear button and an upload button below
        #
        box = gtk.VBox()
        box.set_sensitive(self.running)
        view = gtk.TreeView(self.conduit.store)
        view.connect("row-activated", self._on_row_activated)
        view.set_headers_visible(False)

        box.pack_start(view,expand=True,fill=True)
        bbox = gtk.HButtonBox()
        box.pack_start(bbox,expand=False,fill=True)
        
        #two colums, an icon and a description/name
        col0 = gtk.TreeViewColumn("Pic", gtk.CellRendererPixbuf(), pixbuf=libconduit.ConduitWrapper.PB_IDX)
        view.append_column(col0)
        #second colum is the dataprovider name + status, or the filename 
        nameRenderer = gtk.CellRendererText()
        col1 = gtk.TreeViewColumn("Name", nameRenderer)
        col1.set_cell_data_func(nameRenderer, self._name_data_func)
        view.append_column(col1)
        
        #upload and clear button
        okbtn = gtk.Button(label="Synchronize")
        okbtn.set_image(
                gtk.image_new_from_stock(gtk.STOCK_REFRESH,gtk.ICON_SIZE_BUTTON)
                )
        okbtn.connect("clicked",self._on_sync_clicked, window)
        clearbtn = gtk.Button(stock=gtk.STOCK_CLEAR)
        clearbtn.connect("clicked",self._on_clear_clicked, window)
        bbox.pack_start(okbtn,expand=True)
        bbox.pack_start(clearbtn,expand=True)

        sidebar = window.get_sidebar()
        sidebar.add_page("Photo Uploads", box)
        sidebar.show_all()


        #
        #add items to the tools menu, when clicked the current
        #image is queued with the service to upload
        #
        ui_action_group = gtk.ActionGroup("ConduitPluginActions")
        manager = window.get_ui_manager()

        #make an action for each sink
        for sinkName in SUPPORTED_SINKS:
            desc = SUPPORTED_SINKS[sinkName]
            action = gtk.Action(
                            name=sinkName,
                            stock_id="internet",
                            label=desc,
                            tooltip=""
                        )
            action.connect("activate",self._on_upload_clicked, window)
            ui_action_group.add_action(action)

        manager.insert_action_group(ui_action_group,-1)

        #add each action to the menu
        for sinkName in SUPPORTED_SINKS:
            mid = manager.new_merge_id()
            manager.add_ui(
                    merge_id=mid,
                    path="/MainMenu/ToolsMenu/ToolsOps_2",  #Tools menu
    			    name=sinkName, 
    			    action=sinkName,
    			    type=gtk.UI_MANAGER_MENUITEM, 
    			    top=False)

        #store a reference to the box and action_group as we
        #set them (in)sensitive when conduit is started/stopped
        self.windows[window] = (box, ui_action_group)
    			    
    def _name_data_func(self, column, cell_renderer, tree_model, rowref):
        name = tree_model.get_value(rowref, libconduit.ConduitWrapper.NAME_IDX)
        #render the headers different to the data
        if tree_model.iter_depth(rowref) == 0:
            status = tree_model.get_value(rowref, libconduit.ConduitWrapper.STATUS_IDX)
            name = '%s <span foreground="grey" style="italic">(%s)</span>' % (name,status)
        cell_renderer.set_property("markup", name)

    def activate(self, window):
        self._debug("Activate")
        self._prepare_ui(window) 

    def deactivate(self, window):
        self._debug("Deactivate")
        box,ui_action_group = self.windows[window]
        window.get_sidebar().remove_page(box)
        window.get_ui_manager().remove_action_group(ui_action_group)
        self.conduit.clear()

    def update_ui(self, window):
        self._debug("Update UI")

    def is_configurable(self):
        return False

