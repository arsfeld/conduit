import os.path
import gobject
import gtk
import dbus, dbus.glib

PLUGIN_CONFIG_DIR = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ['HOME'], ".config", "conduit", "plugin-config"))

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"
SYNCSET_DBUS_IFACE="org.conduit.SyncSet"

SYNCSET_GUI_PATH = '/syncset/gui'
SYNCSET_NOGUI_PATH = '/syncset/dbus'

class ConduitWrapper:

    CONFIG_NAME="test-plugin"
    NAME_IDX=0
    URI_IDX=1
    STATUS_IDX=2
    PB_IDX=3

    def __init__(self, syncset, conduit, name, store, debug):
        self.syncset = syncset
        self.conduit = conduit
        self.name = name
        self.store = store
        self.debug = debug
        self.rowref = None
        self.configured = False
        self.pendingSync = False

        self.conduit.connect_to_signal(
                        "SyncProgress",
                        self._on_sync_progress,
                        dbus_interface=CONDUIT_DBUS_IFACE
                        )
        self.conduit.connect_to_signal(
                        "SyncCompleted",
                        self._on_sync_completed,
                        dbus_interface=CONDUIT_DBUS_IFACE
                        )
        self.conduit.connect_to_signal(
                        "SyncStarted",
                        self._on_sync_started,
                        dbus_interface=CONDUIT_DBUS_IFACE
                        )

        self.config_path = os.path.join(PLUGIN_CONFIG_DIR, self.CONFIG_NAME)
        if not os.path.exists(self.config_path):
            self._debug("Creating config dir: %s" % self.config_path)
            try:
                os.makedirs(self.config_path)
            except OSError:
                pass

    def _debug(self, msg):
        if self.debug:
            print "LCW: ", msg

    def _get_configuration(self):
        """
        Gets the latest configuration for a given
        dataprovider
        """
        xml = None
        try:
            if not os.path.exists(os.path.join(self.config_path, self.name)):
                return

            f = open(os.path.join(self.config_path, self.name), 'r')
            xml = f.read()
            f.close()
        except OSError, e:
            self._debug("Error getting config: %s" % e)
        except Exception, e:
            self._debug("Error getting config: %s" % e)

        return xml

    def _save_configuration(self, xml):
        """
        Saves the configuration XML from a given dataprovider again
        """
        try:
            f = open(os.path.join(self.config_path, self.name), 'w')
            f.write(xml)
            f.close()
        except OSError, e:
            self._debug("Error saving config: %s" % e)
        except Exception, e:
            self._debug("Error saving config: %s" % e)

    def _get_rowref(self):
        if self.rowref == None:
            self.add_rowref()
        return self.rowref

    def _configure_reply_handler(self):
        #save the configuration
        xml = self.conduit.SinkGetConfigurationXml()
        self._save_configuration(xml)
        self.configured = True

        #check if a sync was waiting for the conduit (sink) to be configured
        if self.pendingSync == True:
            self.pendingSync = False
            self.conduit.Sync(dbus_interface=CONDUIT_DBUS_IFACE)

    def _configure_error_handler(self, error):
        self._debug("CONFIGURE ERROR: %s" % error)
        self.store.set_value(self._get_rowref(), self.STATUS_IDX, "aborted")

    def _on_sync_started(self):
        self.store.set_value(self._get_rowref(), self.STATUS_IDX, "uploading")

    def _on_sync_progress(self, progress, uids):
        uris = [str(i) for i in uids]
        delete = []

        treeiter = self.store.iter_children(self._get_rowref())
        while treeiter:
            if self.store.get_value(treeiter, self.URI_IDX) in uris:
                delete.append(treeiter)
            treeiter = self.store.iter_next(treeiter)

        for d in delete:
            self.store.remove(d)

        #for uri in uids:
        #    rowref = self._get_rowref_for_photo(str(uri))
        #    print "\t%s - %s" % (uri, rowref)
        #    print "\t",self.photoRefs
        
    def _on_sync_completed(self, abort, error, conflict):
        rowref = self._get_rowref()
        if abort == False and error == False:
            self.clear()
            #update the status
            self.store.set_value(rowref, self.STATUS_IDX, "finished")
        else:
            #show the error message in the conduit gui
            self.store.set_value(rowref, self.STATUS_IDX, "error")

    def _add_uri(self, uri):
        return self.conduit.AddData(uri, dbus_interface=EXPORTER_DBUS_IFACE)

    def _add_item(self, filename, uri, status, pixbuf):
        rowref = self._get_rowref()
        self.store.append(rowref,(
                    filename,       #ConduitWrapper.NAME_IDX
                    uri,            #ConduitWrapper.URI_IDX
                    status,         #ConduitWrapper.STATUS_IDX
                    pixbuf)         #ConduitWrapper.PB_IDX
        )

    def _add_rowref(self, name, uri, status, pixbuf):
        self.rowref = self.store.append(None,(
                            name,   #ConduitWrapper.NAME_IDX
                            uri,    #ConduitWrapper.URI_IDX
                            status, #ConduitWrapper.STATUS_IDX
                            pixbuf) #ConduitWrapper.PB_IDX
        )

    def clear(self):
        rowref = self._get_rowref()
        #delete all the items from the list of items to upload
        delete = []
        child = self.store.iter_children(rowref)
        while child != None:
            delete.append(child)
            child = self.store.iter_next(child)
        #need to do in two steps so we dont modify the store while iterating
        for d in delete:
            self.store.remove(d)
        #delete conduit's remote instance
        self.syncset.DeleteConduit(self.conduit, dbus_interface=SYNCSET_DBUS_IFACE)

    def sync(self):
        if self.configured == True:
            self.conduit.Sync(dbus_interface=CONDUIT_DBUS_IFACE)
        else:
            #defer the sync until the conduit has been configured
            self.pendingSync = True
            #configure the sink and perform the actual synchronisation
            #when the configuration is finished, this way the GUI doesnt
            #block on the call
            self.conduit.SinkConfigure(
                                reply_handler=self._configure_reply_handler,
                                error_handler=self._configure_error_handler,
                                dbus_interface=EXPORTER_DBUS_IFACE
                                )

    def add_item(self, pixbuf, uri):
        if self._add_uri(uri):
            #add to the store
            self._add_item(
                    filename=uri.split("/")[-1],
                    uri=uri,
                    status="",
                    pixbuf=pixbuf
            )

    def add_rowref(self):
        raise NotImplementedError

class ConduitApplicationWrapper(gobject.GObject):

    __gsignals__ = {
        "conduit-started" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_BOOLEAN]),
        }
       
    def __init__(self, conduitWrapperKlass, addToGui, store=True, debug=False):
        gobject.GObject.__init__(self)
        self.conduitWrapperKlass = conduitWrapperKlass
        self.addToGui = addToGui
        self.debug = debug
        self.app = None
        self.conduits = {}
        self.dps = []

        if store:
            #the liststore with icons of the images to be uploaded        
            self.store = gtk.TreeStore(
                                str,                #ConduitWrapper.NAME_IDX
                                str,                #ConduitWrapper.URI_IDX
                                str,                #ConduitWrapper.STATUS_IDX
                                gtk.gdk.Pixbuf      #ConduitWrapper.PB_IDX
                                )
        else:
            self.store = None

        self.dbus_iface = dbus.Interface(
            dbus.SessionBus().get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), 
            'org.freedesktop.DBus'
        )
        self.dbus_iface.connect_to_signal("NameOwnerChanged", self._on_name_owner_changed)

    def _debug(self, msg):
        if self.debug:
            print "LCA: ", msg

    def _get_conduit_app(self):
        try:
            self.app = dbus.Interface(
                        dbus.SessionBus().get_object(APPLICATION_DBUS_IFACE,"/"),
                        APPLICATION_DBUS_IFACE
            )
        except dbus.exceptions.DBusException:
            self._debug("Could not connect to conduit")
            self.app = None
        return self.app

    def _get_available_dps(self):
        if self.app != None:
            self.dps = self.app.GetAllDataProviders()

    def _on_name_owner_changed(self, name, oldOwner, newOwner):
        if name == APPLICATION_DBUS_IFACE:
            if self.dbus_iface.NameHasOwner(APPLICATION_DBUS_IFACE):
                self._get_conduit_app()
                self._get_available_dps()
                self._debug("Conduit started")
            else:
                self._debug("Conduit stopped")
                self.app = None
                self.dps = []
            self.emit("conduit-started", self.connected())

    def build_conduit(self, sinkName):
        a = self.get_dataproviders()
        if sinkName in a:
            realName = a[sinkName]
            self._debug("Building exporter conduit %s (%s)" % (sinkName, realName))

            bus = dbus.SessionBus()

            exporter_path = self.app.BuildExporter(realName)
            exporter = bus.get_object(CONDUIT_DBUS_IFACE, exporter_path)

            if self.addToGui:
                ss = bus.get_object(SYNCSET_DBUS_IFACE, SYNCSET_GUI_PATH)
            else:
                ss = bus.get_object(SYNCSET_DBUS_IFACE, SYNCSET_NOGUI_PATH)
            ss.AddConduit(exporter, dbus_interface=SYNCSET_DBUS_IFACE)

            self.conduits[sinkName] = self.conduitWrapperKlass(
                                                syncset=ss,
                                                conduit=exporter,
                                                name=sinkName,
                                                store=self.store,
                                                debug=self.debug
            )
        else:
            self._debug("Could not build Conduit %s" % sinkName)

    def get_application(self):
        return self.app

    def get_dataproviders(self):
        #Split of the key part of the name
        a = {}
        for n in self.dps:
            a[n.split(":")[0]] = str(n)
        return a

    def upload(self, name, uri, pixbuf):
        if self.connected():
            if name not in self.conduits:
                self.build_conduit(name)

            if uri != None:
                self.conduits[name].add_item(
                                    pixbuf=pixbuf,
                                    uri=uri
                                    )

    def connect_to_conduit(self, startConduit):
        #check if conduit is running
        if self.dbus_iface.NameHasOwner(APPLICATION_DBUS_IFACE):
            self._debug("Conduit already running")
            self._get_conduit_app()
            self._get_available_dps()
            return True
        elif startConduit:
            self._debug("Starting conduit via DBus activation")
            self.dbus_iface.StartServiceByName(APPLICATION_DBUS_IFACE, 0)
            return False
        else:
            #not running, not started
            return False

    def sync(self):
        if self.connected():
            for c in self.conduits:
                self.conduits[c].sync()

    def clear(self):
        if self.connected():
            for name,c in self.conduits.items():
                c.clear()
                if self.store and c.rowref:
                    self.store.remove(c.rowref)
                del(self.conduits[name])

    def connected(self):
        return self.app != None

