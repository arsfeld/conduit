import os

import eog
import gtk, gtk.glade
import dbus, dbus.glib

#if this code is a bit convoluted and jumps around a lot
#it is because I lazy initialize everything to minimise 
#the work that occurs at startup time

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

MENU_PATH="/MainMenu/ToolsMenu/ToolsOps_2"

class ConduitWrapper:
    SUPPORTED_SINKS = ["FlickrSink", "TestSink"]

    def __init__(self):
        self.app = None
        self.conduits = {}
        self.store = gtk.TreeStore(gtk.gdk.Pixbuf,str)

        #setup the DBus connection
        self._connect_to_conduit()

    def _connect_to_conduit(self):
            bus = dbus.SessionBus()
            try:
                remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
                self.app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)

                dps = self.app.GetAllDataProviders()
                for s in ConduitWrapper.SUPPORTED_SINKS:
                    if s in dps:
                        print "Configuring support for %s" % s
                        path = self.app.BuildExporter(s)
                        exporter = bus.get_object(CONDUIT_DBUS_IFACE,path)
                        self.conduits[s] = exporter
            
            except dbus.exceptions.DBusException:
                self.app = None
                print "Conduit unavailable"

    def upload(self, sinkName, eogImage):
        print "Upload ",eogImage
        if self.app != None:
            if sinkName in self.conduits.keys():
                uri = eogImage.get_uri_for_display()
                thumb = eogImage.get_thumbnail()

                print "Adding ", uri

                self.conduits[sinkName].AddData(
                                            uri,
                                            dbus_interface=EXPORTER_DBUS_IFACE
                                            )
                
                #img = gtk.gdk.pixbuf_new_from_file(os.path.join(self.dir, "conduit-icon.png"))
                self.store.append(None,(thumb, uri))

    def sync(self):
        for c in self.conduits.values():
            c.Sync(dbus_interface=CONDUIT_DBUS_IFACE)

class ConduitPlugin(eog.Plugin):
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(__file__, ".."))
        self.gladefile = os.path.join(self.dir, "config.glade")
        
        self.conduit = ConduitWrapper()

    def _on_act(self, sender, window):
        currentImage = window.get_image()
        self.conduit.upload("TestSink", currentImage)

    def _on_sync_clicked(self, *args):
        self.conduit.sync()

    def _prepare_sidebar(self, window):
        #the sidebar is a treeview where 
        #photos to upload are grouped by the
        #upload service, with a clear button and
        #a upload button below

        box = gtk.VBox()
        view = gtk.TreeView(self.conduit.store)
        box.pack_start(view,expand=True,fill=True)
        bbox = gtk.HButtonBox()
        box.pack_start(bbox,expand=False)
        
        #two colums, a icon and a description/name
        col0 = gtk.TreeViewColumn("Pic", gtk.CellRendererPixbuf(), pixbuf=0)
        col1 = gtk.TreeViewColumn("Name", gtk.CellRendererText(), text=1)
        view.append_column(col0)
        view.append_column(col1)
        view.set_headers_visible(False)

        #upload and clear button
        okbtn = gtk.Button(stock=gtk.STOCK_OK)
        okbtn.connect("clicked",self._on_sync_clicked)
        clearbtn = gtk.Button(stock=gtk.STOCK_CLEAR)
        bbox.pack_start(okbtn)
        bbox.pack_start(clearbtn)

        sidebar = window.get_sidebar()
        sidebar.add_page("Conduit", box)
        sidebar.show_all()

    def _prepare_tools_menu(self, window):
        action = gtk.Action(
                        name="RunPostr",
                        stock_id="internet",
                        label="Upload to Flickr",
                        tooltip="Upload your pictures to Flickr"
                        )
        action.connect("activate",self._on_act, window)

        manager = window.get_ui_manager()

        ui_action_group = gtk.ActionGroup("EogPostrPluginActions")
        ui_action_group.add_action(action)

        manager.insert_action_group(ui_action_group,-1)
        mid = manager.new_merge_id()
        manager.add_ui(
                merge_id=mid,
                path=MENU_PATH,
			    name="RunPostr", 
			    action="RunPostr",
			    type=gtk.UI_MANAGER_MENUITEM, 
			    top=False)

    def activate(self, window):
        #the sidebar and menu integration must be done once per eog window instance
        self._prepare_sidebar(window) 
        self._prepare_tools_menu(window)
        print "ACTIVATE"

    def deactivate(self, window):
        print "DEACTIVATE"

    def update_ui(self, window):
        print "UPDATE"

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        xml = gtk.glade.XML(self.gladefile, "ConfigDialog")
        dlg = xml.get_widget("ConfigDialog")
        return dlg
