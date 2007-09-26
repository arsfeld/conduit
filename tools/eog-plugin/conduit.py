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
    "PicasaTwoWay"      :   "Upload to Picasa",
    "SmugMugTwoWay"     :   "Uploat to SmugMug",
    "BoxDotNetTwoWay"   :   "Upload to Box.net"
}

ICON_SIZE = 24

CONFIG_PATH='~/.conduit/eog-plugin'

class ConduitWrapper:
    def __init__(self, conduit, name, store):
        self.conduit = conduit
        self.name = name
        self.store = store
        self.rowref = None
        self.configured = False

        self.pendingSync = False

    def _get_configuration(self):
        """
        Gets the latest configuration for a given
        dataprovider
        """
        config_path = os.path.expanduser(CONFIG_PATH)

        if not os.path.exists(os.path.join(config_path, self.name)):
           return

        f = open(os.path.join(config_path, self.name), 'r')
        xml = f.read ()
        f.close()

        return xml
           
    def _save_configuration(self, xml):
        """
        Saves the configuration xml from a given dataprovider again
        """
        config_path = os.path.expanduser(CONFIG_PATH)

        if not os.path.exists(config_path):
           os.mkdir(config_path)

        f = open(os.path.join(config_path, self.name), 'w')
        f.write(xml)
        f.close()

    def _get_rowref(self):
        if self.rowref == None:
            #store the rowref in the store with the icon conduit gave us
            info = self.conduit.SinkGetInformation(dbus_interface=EXPORTER_DBUS_IFACE)
            pb = gtk.gdk.pixbuf_new_from_file_at_size(info['icon_path'], ICON_SIZE, ICON_SIZE)
            desc = SUPPORTED_SINKS[self.name]
            self.rowref = self.store.append(None,(pb, desc))
        return self.rowref

    def _configure_reply_handler(self):            
        #save the configuration
        xml = self.conduit.SinkGetConfigurationXml()
        self._save_configuration(xml)
        self.configured = True
        print "Configured"

        #check if a sync was waiting for the conduit (sink) to be configured
        if self.pendingSync == True:
            self.pendingSync = False
            self.conduit.Sync(dbus_interface=CONDUIT_DBUS_IFACE)

    def _configure_error_handler(self, error):
        pass

    def add_photo(self, pixbuf, uri):
        ok = self.conduit.AddData(uri,dbus_interface=EXPORTER_DBUS_IFACE)
        if ok == True:
            #add to the store
            rowref = self._get_rowref()
            filename = uri.split("/")[-1]
            self.store.append(rowref,(pixbuf, filename))

    def sync(self):
        if self.configured == True:
            self.conduit.Sync(dbus_interface=CONDUIT_DBUS_IFACE)
        else:
            #defer the sync until the conduit has been configured
            self.pendingSync = True
            # configure the sink; and perform the actual synchronisation
            # when the configuration is finished, this way the eog gui doesnt
            # block on the call
            self.conduit.SinkConfigure(
                                reply_handler=self._configure_reply_handler,
                                error_handler=self._configure_error_handler,
                                dbus_interface=EXPORTER_DBUS_IFACE
                                )

class ConduitApplicationWrapper:
    def __init__(self):
        #conduit dbus application
        self.app = None
        #the conduit dbus objects
        self.conduits = {}
        #the liststore with icons of the images to be uploaded        
        self.store = gtk.TreeStore(gtk.gdk.Pixbuf,str)

        #setup the DBus connection
        self._connect_to_conduit_application()

    def _connect_to_conduit_application(self):
            try:
                remote_object = dbus.SessionBus().get_object(APPLICATION_DBUS_IFACE,"/")
                self.app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)
                self.dps = self.app.GetAllDataProviders() 

            except dbus.exceptions.DBusException:
                self.app = None
                print "Conduit unavailable"

    def _build_conduit(self, sinkName):
        if sinkName in self.dps:
            print "Building exporter conduit %s" % sinkName
            path = self.app.BuildExporter(sinkName)
            exporter = dbus.SessionBus().get_object(CONDUIT_DBUS_IFACE,path)
            self.conduits[sinkName] = ConduitWrapper(conduit=exporter, name=sinkName, store=self.store)

    def upload(self, name, eogImage):
        if self.app != None:
            if name not in self.conduits:
                self._build_conduit(name)

            imageuri = eogImage.get_uri_for_display()
            
            #proportionally scale the pixbuf            
            thumb = eogImage.get_thumbnail()
            pb = thumb.scale_simple(ICON_SIZE,ICON_SIZE,gtk.gdk.INTERP_BILINEAR)

            #add the photo to the remote condui and the liststore
            print "Upload ", name, eogImage
            self.conduits[name].add_photo(pixbuf=pb,uri=imageuri)

    def sync(self):
        for c in self.conduits:
            self.conduits[c].sync()

class ConduitPlugin(eog.Plugin):
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(__file__, ".."))
        self.gladefile = os.path.join(self.dir, "config.glade")
        
        self.conduit = ConduitApplicationWrapper()

    def _on_act(self, sender, window):
        currentImage = window.get_image()
        name = sender.get_property("name")
        self.conduit.upload(name, currentImage)

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
        for sinkName in SUPPORTED_SINKS:
            desc = SUPPORTED_SINKS[sinkName]
            action = gtk.Action(
                            name=sinkName,
                            stock_id="internet",
                            label=desc,
                            tooltip=""
                        )
            action.connect("activate",self._on_act, window)
            ui_action_group.add_action(action)

        manager.insert_action_group(ui_action_group,-1)

        #add each action to the menu
        for sinkName in SUPPORTED_SINKS:
            mid = manager.new_merge_id()
            manager.add_ui(
                    merge_id=mid,
                    path=MENU_PATH,
    			    name=sinkName, 
    			    action=sinkName,
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
