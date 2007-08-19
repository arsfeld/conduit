import os
import getopt
import sys
import dbus, dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import conduit
import conduit.Utils as Utils
from conduit import log,logd,logw
from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
from conduit.SyncSet import SyncSet

import conduit.VolumeMonitor as gnomevfs

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
        self.uiLib = None

        #Default command line values
        if conduit.IS_DEVELOPMENT_VERSION:
            settingsFile = os.path.join(conduit.USER_DIR, "settings-dev.xml")
            dbFile = os.path.join(conduit.USER_DIR, "mapping-dev.db")
        else:
            settingsFile = os.path.join(conduit.USER_DIR, "settings.xml")
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
                     settingsFile = os.path.join(os.getcwd(), a)
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
        memstats = conduit.memstats()
        
        #Dynamically import the GUI
        self.uiLib = __import__(ui)

        #FIXME: attempt workaround for gnomvefs bug...
        #this shouldn't need to be here, but if we call it after 
        #touching the session bus then nothing will work
        gnomevfs.VolumeMonitor()

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
                    conduitApp.BuildGUI(settingsFile)
                    conduitApp.ShowGUI()
                    conduitApp.HideSplash()
            sys.exit(0)

        # Initialise dbus stuff here as any earlier will cause breakage
        # 1: Outstanding gnomevfs bug!
        # 2: Interferes with Conduit already running check.
        bus_name = dbus.service.BusName(APPLICATION_DBUS_IFACE, bus=sessionBus)
        dbus.service.Object.__init__(self, bus_name, "/activate")

        #Throw up a splash screen ASAP. Dont show if launched via --console.
        if buildGUI and not iconify:
            self.ShowSplash()

        #Dynamically load all datasources, datasinks and converters
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            os.path.join(conduit.USER_DIR, "modules")
                            ]
        #the moduleManager and typeConverter are shared between DBus and GUI
        self.moduleManager = ModuleManager(dirs_to_search)
        self.typeConverter = TypeConverter(self.moduleManager)

        #The status icon is shared between the GUI and the Dbus iface
        if conduit.settings.get("show_status_icon") == True:
            self.statusIcon = self.uiLib.StatusIcon(self)
           
        #Set up the application wide defaults
        conduit.mappingDB.open_db(dbFile)

        #Set the view models
        if buildGUI:
            self.BuildGUI(settingsFile)
            #FIXME: Cannot do correct behavior without flashing due to crasher bug
            if iconify:
                self.IconifyGUI()
            #if not iconify:
            #    self.ShowGUI()
        
        #Dbus view...
        if conduit.settings.get("enable_dbus_interface") == True:
            from conduit.DBus import DBusView
            self.dbus = DBusView(
                            conduitApplication=self,
                            moduleManager=self.moduleManager,
                            typeConverter=self.typeConverter
                            )
            #Dbus manages its own model per caller
            self.dbus.set_model(None)

            if self.statusIcon:
                self.dbus.sync_manager.add_syncworker_callbacks(
                                        self.statusIcon.on_sync_started,
                                        self.statusIcon.on_sync_completed,
                                        self.statusIcon.on_sync_conflict,
                                        None
                                        )

        #hide the splash screen
        self.HideSplash()

        conduit.memstats(memstats)
        try:
            self.uiLib.main_loop()
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

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='s', out_signature='')
    def BuildGUI(self, settingsFile):
        self.gui = self.uiLib.MainWindow(
                        conduitApplication=self,
                        moduleManager=self.moduleManager,
                        typeConverter=self.typeConverter
                        )

        #FIXME: need to show gui to stop goocanvas crash
        self.gui.mainWindow.show_all()

        #reload the saved sync set
        syncSet = SyncSet(
                        moduleManager=self.moduleManager,
                        xmlSettingFilePath=settingsFile
                        )
        syncSet.restore_from_xml()
        self.gui.set_model(syncSet)

        if self.statusIcon:
            self.gui.sync_manager.add_syncworker_callbacks(
                                    self.statusIcon.on_sync_started,
                                    self.statusIcon.on_sync_completed,
                                    self.statusIcon.on_sync_conflict,
                                    None
                                    )

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowGUI(self):
        self.gui.present()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def ShowSplash(self):
        if conduit.settings.get("show_splashscreen") == True:
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
        log("Closing application")
        if self.gui != None:
            self.gui.mainWindow.hide()
            if conduit.settings.get("save_on_exit") == True:
                self.gui.save_settings(None)
            log("Stopping GUI synchronization threads")
            self.gui.sync_manager.cancel_all()

        if self.dbus != None:
            log("Stopping DBus synchronization threads")
            self.dbus.sync_manager.cancel_all()

        #give the dataprovider factories time to shut down
        self.moduleManager.quit()

        self.uiLib.main_quit()

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Synchronize(self):
        if self.gui != None:
            self.gui.on_synchronize_all_clicked(None)
