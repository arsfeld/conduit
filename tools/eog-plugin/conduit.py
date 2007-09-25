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

SUPPORTED_SINKS = {
    "FlickrTwoWay"      :   "Upload to Flickr",
#    "PicasaTwoWay"      :   "Upload to Picasa",
#    "SmugMugTwoWay"     :   "Uploat to SmugMug",
#    "BoxDotNetTwoWay"   :   "Upload to Box.net"
}

ICON_SIZE = 24

CONFIG_PATH='~/.conduit/eog-plugin'

class ConduitApplicationWrapper:
    def __init__(self):
        self.app = None

        #the conduit dbus objects
        self.conduits = {}
        #rowrefs of parents in the store.
        self.storeConduits = {}
        #record if the conduit has been configured or not
        self.configured = {}
        
        self.store = gtk.TreeStore(gtk.gdk.Pixbuf,str)

        #setup the DBus connection
        self._connect_to_conduit()

    def _get_configuration(self, sink_name):
        """
        Gets the latest configuration for a given
        dataprovider
        """
        config_path = os.path.expanduser(CONFIG_PATH)

        if not os.path.exists(os.path.join(config_path, sink_name)):
           return

        f = open(os.path.join(config_path, sink_name), 'r')
        xml = f.read ()
        f.close()

        return xml
           
    def _save_configuration(self, sink_name, xml):
        """
        Saves the configuration xml from a given dataprovider again
        """
        config_path = os.path.expanduser(CONFIG_PATH)

        if not os.path.exists(config_path):
           os.mkdir(config_path)

        f = open(os.path.join(config_path, sink_name), 'w')
        f.write(xml)
        f.close()

    def _connect_to_conduit(self):
            try:
                remote_object = dbus.SessionBus().get_object(APPLICATION_DBUS_IFACE,"/")
                self.app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)
                self.dps = self.app.GetAllDataProviders() 

            except dbus.exceptions.DBusException:
                self.app = None
                print "Conduit unavailable"

    def _build_exporter(self, dp):
        if dp in self.dps:
            print "Configuring support for %s" % dp
            path = self.app.BuildExporter(dp)
            exporter = dbus.SessionBus().get_object(CONDUIT_DBUS_IFACE,path)
            self.conduits[dp] = exporter

    def _get_store_parent(self, dp):
        #top level items in the list store are icons for the dataprovider in use
        #this function creates them if needed otherwise returns their rowref
        if dp not in self.storeConduits:
            info = self.conduits[dp].SinkGetInformation(dbus_interface=EXPORTER_DBUS_IFACE)
            pb = gtk.gdk.pixbuf_new_from_file_at_size(info['icon_path'], ICON_SIZE, ICON_SIZE)
            #store the rowref
            self.storeConduits[dp] = self.store.append(None,(pb, SUPPORTED_SINKS[dp]))

    def _configure_reply_handler(self):            
        #save the configuration
        #xml = self.conduits[c].SinkGetConfigurationXml()
        #self._save_configuration(c, xml)
        #self.configured:
        self.configured["FlickrTwoWay"] = True
        print "Configured"

    def _configure_error_handler(self, error):
        pass

    def upload(self, sinkName, eogImage):
        print "Upload ", sinkName, eogImage
        if self.app != None:
            if sinkName not in self.conduits:
                self._build_exporter(sinkName)

            uri = eogImage.get_uri_for_display()
            thumb = eogImage.get_thumbnail()

            ok = self.conduits[sinkName].AddData(
                                        uri,
                                        dbus_interface=EXPORTER_DBUS_IFACE
                                        )
            print "OK ",ok
            if ok == True:
                #add to the rowstore
                rowref = self._get_store_parent(sinkName)
                pb = thumb.scale_simple(ICON_SIZE,ICON_SIZE,gtk.gdk.INTERP_BILINEAR)
                filename = uri.split("/")[-1]
                self.store.append(rowref,(pb, filename))

    def sync(self):
        for c in self.conduits:
            if c in self.configured:
                self.conduits[c].Sync(dbus_interface=CONDUIT_DBUS_IFACE)
            else:
                # configure the sink; and perform the actual synchronisation
                # when the configuration is finished, this way the eog gui doesnt
                # block on the call
                self.conduits[c].SinkConfigure(
                                    reply_handler=self._configure_reply_handler,
                                    error_handler=self._configure_error_handler,
                                    dbus_interface=EXPORTER_DBUS_IFACE
                                    )
               


class ConduitPlugin(eog.Plugin):
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(__file__, ".."))
        self.gladefile = os.path.join(self.dir, "config.glade")
        
        self.conduit = ConduitApplicationWrapper()

    def _on_act(self, sender, window):
        currentImage = window.get_image()
        dpname = sender.get_property("name")
        self.conduit.upload(dpname, currentImage)

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
        ui_action_group = gtk.ActionGroup("ConduitPluginActions")
        manager = window.get_ui_manager()

        #make an action for each sink
        for dp in SUPPORTED_SINKS:
            desc = SUPPORTED_SINKS[dp]
            action = gtk.Action(
                            name=dp,
                            stock_id="internet",
                            label=desc,
                            tooltip=""
                        )
            action.connect("activate",self._on_act, window)
            ui_action_group.add_action(action)

        manager.insert_action_group(ui_action_group,-1)

        #add each action to the menu
        for dp in SUPPORTED_SINKS:
            mid = manager.new_merge_id()
            manager.add_ui(
                    merge_id=mid,
                    path=MENU_PATH,
    			    name=dp, 
    			    action=dp,
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
        return False

    def create_configure_dialog(self):
        xml = gtk.glade.XML(self.gladefile, "ConfigDialog")
        dlg = xml.get_widget("ConfigDialog")
        return dlg
