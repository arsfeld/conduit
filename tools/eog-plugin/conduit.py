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

class ConduitPlugin(eog.Plugin):
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(__file__, ".."))
        self.gladefile = os.path.join(self.dir, "config.glade")
        self.store = gtk.TreeStore(gtk.gdk.Pixbuf,str)

        self.act = gtk.Action(
                        name="RunPostr",
                        stock_id="internet",
                        label="Upload to Flickr",
                        tooltip="Upload your pictures to Flickr"
                        )
        self.act.connect("activate",self._on_act)
        
        self.dlg = None
        self.app = None

    def _on_act(self, *args):
        print "CLICK"

    def _dummy_data(self):
        img = gtk.gdk.pixbuf_new_from_file(os.path.join(self.dir, "conduit-icon.png"))
        self.store.append(None,(img, "Text"))

    def _connect_to_conduit(self):
        #Create an Interface wrapper for the remote object
        bus = dbus.SessionBus()

        try:
            remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
            self.app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)

            dps = self.app.GetAllDataProviders()
            print "Available DPs"
            for dp in dps:
                print " * ",dp
        except dbus.exceptions.DBusException:
            print "Conduit unavailable"

    def _prepare_sidebar(self, window):
        #the sidebar is a treeview where 
        #photos to upload are grouped by the
        #upload service, with a clear button and
        #a upload button below

        box = gtk.VBox()
        view = gtk.TreeView(self.store)
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
        clearbtn = gtk.Button(stock=gtk.STOCK_CLEAR)
        bbox.pack_start(okbtn)
        bbox.pack_start(clearbtn)

        sidebar = window.get_sidebar()
        sidebar.add_page("Conduit", box)
        sidebar.show_all()

    def _prepare_tools_menu(self, window):
        manager = window.get_ui_manager()

        ui_action_group = gtk.ActionGroup("EogPostrPluginActions")
        ui_action_group.add_action(self.act)

        manager.insert_action_group(ui_action_group,-1)
        mid = manager.new_merge_id()
        manager.add_ui(
                merge_id=mid,
                path=MENU_PATH,
			    name="RunPostr", 
			    action="RunPostr",
			    type=gtk.UI_MANAGER_MENUITEM, 
			    top=False)

    def _prepare_config_dialog(self):
        if self.dlg == None:
            xml = gtk.glade.XML(self.gladefile, "ConfigDialog")
            self.dlg = xml.get_widget("ConfigDialog")

    def activate(self, window):
        self._connect_to_conduit()
        self._prepare_sidebar(window) 
        self._prepare_tools_menu(window)
        self._dummy_data()       
        print "ACTIVATE"

    def deactivate(self, window):
        print "DEACTIVATE"

    def update_ui(self, window):
        print "UPDATE"

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        self._prepare_config_dialog()
        return self.dlg
