import os
import getopt
import sys
import dbus, dbus.service, dbus.mainloop.glib
import gobject

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
dbus.mainloop.glib.threads_init()

import logging
log = logging.getLogger("Main")

import conduit
import conduit.utils as Utils
from conduit.Module import ModuleManager
from conduit.MappingDB import MappingDB
from conduit.TypeConverter import TypeConverter
from conduit.SyncSet import SyncSet
from conduit.Synchronization import SyncManager
from conduit.DBus import DBusInterface
from conduit.Settings import Settings

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
        self.uiLib = None

        gobject.set_application_name("Conduit")
        self.settingsFile = os.path.join(conduit.USER_DIR, "settings.xml")
        self.dbFile = os.path.join(conduit.USER_DIR, "mapping.db")

        #initialize application settings
        conduit.GLOBALS.settings = Settings()

        buildGUI = True
        iconify = False
        whitelist = None
        blacklist = None
        self.ui = "gtk"
        settings = {}
        try:
            opts, args = getopt.getopt(
                            sys.argv[1:],
                            "hvf:ciu:w:x:s:",
                                ("help", "version", "config-file=",
                                 "console", "iconify", "ui=", "with-modules=",
                                 "without-modules=", "settings="))
            #parse args
            for o, a in opts:
                if o in ("-h", "--help"):
                    self._usage()
                    sys.exit(0)
                if o in ("-v", "--version"):
                    print "Conduit %s" % conduit.VERSION
                    sys.exit(0)
                if o in ("-f", "--config-file"):
                     self.settingsFile = os.path.join(os.getcwd(), a)
                if o in ("-c", "--console"):
                   buildGUI = False
                if o in ("-i", "--iconify"):
                    iconify = True
                if o in ("-u", "--ui"):
                    self.ui = a
                if o in ("-w", "--with-modules"):
                    whitelist = a.split(",")
                if o in ("-x", "--without-modules"):
                    blacklist = a.split(",")
                if o in ("-s", "--settings"):
                    try:
                        for i in a.split(','):
                            k,v = i.split('=')
                            settings[k] = v
                    except: pass
                    conduit.GLOBALS.settings.set_overrides(**settings)

        except getopt.GetoptError:
            log.warn("Unknown command line option")
            self._usage()
            sys.exit(1)

        log.info("Conduit v%s Installed: %s" % (conduit.VERSION, conduit.IS_INSTALLED))
        log.info("Python: %s" % sys.version)
        log.info("Platform Implementations: %s,%s,%s" % (conduit.FILE_IMPL,conduit.BROWSER_IMPL, conduit.SETTINGS_IMPL))
        if settings:
            log.info("Settings have been overridden: %s" % settings)
        
        #Make conduit single instance. If conduit is already running then
        #make the original process build or show the gui
        sessionBus = dbus.SessionBus()
        if Utils.dbus_service_available(APPLICATION_DBUS_IFACE, sessionBus):
            log.info("Conduit is already running")
            obj = sessionBus.get_object(APPLICATION_DBUS_IFACE, "/activate")
            conduitApp = dbus.Interface(obj, APPLICATION_DBUS_IFACE)
            if buildGUI:
                if conduitApp.HasGUI():
                    conduitApp.ShowGUI()
                else:
                    conduitApp.ImportGUI()
                    conduitApp.ShowSplash()
                    conduitApp.ShowStatusIcon()
                    conduitApp.BuildGUI()
                    conduitApp.ShowGUI()
                    conduitApp.HideSplash()
            sys.exit(0)

        # Initialise dbus stuff here as any earlier will interfere
        # with Conduit already running check.
        bus_name = dbus.service.BusName(APPLICATION_DBUS_IFACE, bus=sessionBus)
        dbus.service.Object.__init__(self, bus_name, "/activate")
        
        #Throw up a splash screen ASAP. Dont show anything if launched via --console.
        if buildGUI:
            log.info("Using UI: %s" % self.ui)
            self.ImportGUI()
            if not iconify:
                self.ShowSplash()
            self.ShowStatusIcon()

        #Dynamically load all datasources, datasinks and converters
        dirs_to_search =    [
                            conduit.SHARED_MODULE_DIR,
                            os.path.join(conduit.USER_DIR, "modules")
                            ]

        #Initialize all globals variables
        conduit.GLOBALS.app = self
        conduit.GLOBALS.moduleManager = ModuleManager(dirs_to_search)
        conduit.GLOBALS.moduleManager.load_all(whitelist, blacklist)
        conduit.GLOBALS.typeConverter = TypeConverter(conduit.GLOBALS.moduleManager)
        conduit.GLOBALS.syncManager = SyncManager(conduit.GLOBALS.typeConverter)
        conduit.GLOBALS.mappingDB = MappingDB(self.dbFile)
        conduit.GLOBALS.mainloop = gobject.MainLoop()
        
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
            conduit.GLOBALS.mainloop.run()
        except KeyboardInterrupt:
            self.Quit()

    def _usage(self):
        print """Usage: conduit [OPTIONS] - Synchronize things
OPTIONS:
    -h, --help                  Show this message.
    -c, --console               Launch with no GUI.
                                (default=no)
    -f, --config-file=FILE      Save dataprovider configuration to FILE.
                                (default=$XDG_CONFIG_DIR/.conduit/settings.xml)
    -i, --iconify               Iconify on startup.
                                (default=no)
    -u, --ui=NAME               Run with the specified UI.
                                (default=gtk)
    -w, --with-modules          Only load modules in the named files.
                                (default=load all modules)
    -x, --without-modules       Do not load modules in the named files.
                                (default=load all modules)
    -s, --settings=key=val,..   Explicitly set internal Conduit settings (keys)
                                to the given values for this session.
    -v, --version               Show version information."""

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='b')
    def HasGUI(self):
        return self.gui != None

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def BuildGUI(self):
        self.gui = self.uiLib.MainWindow(
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
    def ImportGUI(self):
        if self.uiLib == None:
            self.uiLib = __import__("conduit.%sui.UI" % self.ui, {}, {}, ['UI'])

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowGUI(self):
        self.gui.present()
        
    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowStatusIcon(self):
        #The status icon is shared between the GUI and the Dbus iface
        if conduit.GLOBALS.settings.get("show_status_icon") == True:
            self.statusIcon = self.uiLib.StatusIcon(self)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowSplash(self):
        if conduit.GLOBALS.settings.get("show_splashscreen") == True:
            self.splash = self.uiLib.SplashScreen()
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
        #Hide the GUI first, so we feel responsive    
        log.info("Closing application")
        if self.gui != None:
            self.gui.mainWindow.hide()
            if conduit.GLOBALS.settings.get("save_on_exit") == True:
                self.gui.save_settings(None)

        #Cancel all syncs
        self.Cancel()

        #give the dataprovider factories time to shut down
        log.info("Closing dataprovider factories")
        conduit.GLOBALS.moduleManager.quit()
        
        #unitialize all dataproviders
        log.info("Unitializing dataproviders")
        self.guiSyncSet.quit()
        log.info("GUI Quit")
        self.dbusSyncSet.quit()
        log.info("DBus Quit")

        #Save the mapping DB
        conduit.GLOBALS.mappingDB.save()
        conduit.GLOBALS.mappingDB.close()

        #Save the application settings
        conduit.GLOBALS.settings.save()
        
        log.info("Main Loop Quitting")
        conduit.GLOBALS.mainloop.quit()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Synchronize(self):
        for cond in self.guiSyncSet.get_all_conduits():
            if cond.datasource is not None and len(cond.datasinks) > 0:
                conduit.GLOBALS.syncManager.sync_conduit(cond)
            else:
                log.info("Conduit must have a datasource and a datasink")
                
    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Cancel(self):
        #flag the global cancellation object
        log.info("Setting global cancel flag")
        conduit.GLOBALS.cancelled = True

        #cancel all conduits
        log.info("Stopping Synchronization threads")
        conduit.GLOBALS.syncManager.cancel_all()

