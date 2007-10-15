import os
import getopt
import sys
import dbus, dbus.service, dbus.glib

import conduit
import conduit.Utils as Utils
from conduit import log,logd,logw
from conduit.Module import ModuleManager
from conduit.MappingDB import MappingDB
from conduit.TypeConverter import TypeConverter
from conduit.SyncSet import SyncSet
from conduit.Synchronization import SyncManager
from conduit.DBus import DBusInterface
from conduit.GtkUI import SplashScreen, MainWindow, StatusIcon, main_loop, main_quit

APPLICATION_DBUS_IFACE="org.conduit.Application"

class Application(dbus.service.Object):
    def __init__(self):
        """
        Conduit application class
        Parses command line arguments. Sets up the views and models;
        restores application settings, shows the splash screen and the UI

        Notes: 
            1) If conduit is launched without --console switch then the gui
            and the console interfaces are started
            2) If launched with --console and then later via the gui then set 
            up the gui and connect all the appropriate signal handlers
        """
        self.splash = None
        self.gui = None
        self.statusIcon = None
        self.dbus = None

        self.guiSyncSet = None
        self.dbusSyncSet = None

        #Default command line values
        if conduit.IS_DEVELOPMENT_VERSION:
            self.settingsFile = os.path.join(conduit.USER_DIR, "settings-dev.xml")
            dbFile = os.path.join(conduit.USER_DIR, "mapping-dev.db")
        else:
            self.settingsFile = os.path.join(conduit.USER_DIR, "settings.xml")
            dbFile = os.path.join(conduit.USER_DIR, "mapping.db")

        buildGUI = True
        iconify = False
        ui = "GtkUI"
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hs:ciu:", 
                ["help", "settings=", "console", "iconify", "ui="])
            #parse args
            for o, a in opts:
                if o in ("-h", "--help"):
                    self._usage()
                    sys.exit(0)
                if o in ("-s", "--settings"):
                     self.settingsFile = os.path.join(os.getcwd(), a)
                if o in ("-c", "--console"):
                   buildGUI = False
                if o in ("-i", "--iconify"):
                    iconify = True
                if o in ("-u", "--ui"):
                     ui = a
        except getopt.GetoptError:
            # print help information and exit:
            logw("Unknown command line option")
            self._usage()
            sys.exit(1)

        log("Conduit v%s Installed: %s" % (conduit.APPVERSION, conduit.IS_INSTALLED))
        log("Log Level: %s" % conduit.LOG_LEVEL)
        log("Using UI: %s" % ui)
        
        #Make conduit single instance. If conduit is already running then
        #make the original process build or show the gui
        sessionBus = dbus.SessionBus()
        if Utils.dbus_service_available(sessionBus, APPLICATION_DBUS_IFACE):
            log("Conduit is already running")
            obj = sessionBus.get_object(APPLICATION_DBUS_IFACE, "/activate")
            conduitApp = dbus.Interface(obj, APPLICATION_DBUS_IFACE)
            if buildGUI:
                if conduitApp.HasGUI():
                    conduitApp.ShowGUI()
                else:
                    conduitApp.ShowSplash()
                    conduitApp.BuildGUI()
                    conduitApp.ShowGUI()
                    conduitApp.HideSplash()
            sys.exit(0)

        # Initialise dbus stuff here as any earlier will interfere
        # with Conduit already running check.
        bus_name = dbus.service.BusName(APPLICATION_DBUS_IFACE, bus=sessionBus)
        dbus.service.Object.__init__(self, bus_name, "/activate")
        
        #Throw up a splash screen ASAP. Dont show if launched via --console.
        if buildGUI and not iconify:
            self.ShowSplash()

        #The status icon is shared between the GUI and the Dbus iface
        if conduit.GLOBALS.settings.get("show_status_icon") == True:
            self.statusIcon = StatusIcon(self)

        #Dynamically load all datasources, datasinks and converters
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            os.path.join(conduit.USER_DIR, "modules")
                            ]

        #Initialize all globals variables
        conduit.GLOBALS.app = self
        conduit.GLOBALS.moduleManager = ModuleManager(dirs_to_search)
        conduit.GLOBALS.typeConverter = TypeConverter(conduit.GLOBALS.moduleManager)
        conduit.GLOBALS.syncManager = SyncManager(conduit.GLOBALS.typeConverter)
        conduit.GLOBALS.mappingDB = MappingDB(dbFile)
        
        #Build both syncsets and put on the bus as early as possible
        self.guiSyncSet = SyncSet(
                        moduleManager=conduit.GLOBALS.moduleManager,
                        syncManager=conduit.GLOBALS.syncManager,
                        xmlSettingFilePath=self.settingsFile
                        )
        self.dbusSyncSet = SyncSet(
                    moduleManager=conduit.GLOBALS.moduleManager,
                    syncManager=conduit.GLOBALS.syncManager
                    )

        #Set the view models
        if buildGUI:
            self.BuildGUI()
            if not iconify:
                self.ShowGUI()
        
        #Dbus view...
        self.dbus = DBusInterface(
                        conduitApplication=self,
                        moduleManager=conduit.GLOBALS.moduleManager,
                        typeConverter=conduit.GLOBALS.typeConverter,
                        syncManager=conduit.GLOBALS.syncManager,
                        guiSyncSet=self.guiSyncSet,
                        dbusSyncSet=self.dbusSyncSet
                        )
        
        if self.statusIcon:
            self.dbusSyncSet.connect("conduit-added", self.statusIcon.on_conduit_added)
            self.dbusSyncSet.connect("conduit-removed", self.statusIcon.on_conduit_removed)

        #hide the splash screen
        self.HideSplash()
        try:
            main_loop()
        except KeyboardInterrupt:
            self.Quit()

    def _usage(self):
        print """Conduit: Usage
$ %s [OPTIONS]

OPTIONS:
    -h, --help          Print this help notice.
    -c, --console       Launch Conduit with no GUI) (default=no).
    -s, --settings=FILE Override saving conduit settings to FILE
    -i, --iconify       Iconify on startup (default=no)""" % sys.argv[0]

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='b')
    def HasGUI(self):
        return self.gui != None

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def BuildGUI(self):
        self.gui = MainWindow(
                        conduitApplication=self,
                        moduleManager=conduit.GLOBALS.moduleManager,
                        typeConverter=conduit.GLOBALS.typeConverter,
                        syncManager=conduit.GLOBALS.syncManager
                        )

        #reload the saved sync set
        self.guiSyncSet.restore_from_xml()
        self.gui.set_model(self.guiSyncSet)

        if self.statusIcon:
            self.guiSyncSet.connect("conduit-added", self.statusIcon.on_conduit_added)
            self.guiSyncSet.connect("conduit-removed", self.statusIcon.on_conduit_removed)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowGUI(self):
        self.gui.present()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowSplash(self):
        if conduit.GLOBALS.settings.get("show_splashscreen") == True:
            self.splash = SplashScreen()
            self.splash.show()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def HideSplash(self):
        if self.splash != None:
            self.splash.destroy()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')        
    def IconifyGUI(self):
        self.gui.minimize_to_tray()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Quit(self):
        log("Closing application")
        if self.gui != None:
            self.gui.mainWindow.hide()
            if conduit.GLOBALS.settings.get("save_on_exit") == True:
                self.gui.save_settings(None)

        #flag the global cancellation object
        log("Setting global cancel flag")
        conduit.GLOBALS.cancelled = True

        #cancel all conduits
        log("Stopping Synchronization threads")
        conduit.GLOBALS.syncManager.cancel_all()

        #give the dataprovider factories time to shut down
        log("Closing dataprovider factories")
        conduit.GLOBALS.moduleManager.quit()
        main_quit()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Synchronize(self):
        if self.gui != None:
            self.gui.on_synchronize_all_clicked(None)
