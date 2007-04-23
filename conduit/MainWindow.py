"""
Draws the applications main window

Also manages the callbacks from menu and GUI items

Copyright: John Stowers, 2006
License: GPLv2
"""
import gobject
import gtk, gtk.glade
import gnome.ui
import os.path
import getopt, sys
from gettext import gettext as _

import dbus, dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib


import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
from conduit.DBus import DBusView
from conduit.Module import ModuleManager
from conduit.Canvas import Canvas
from conduit.Synchronization import SyncManager
from conduit.TypeConverter import TypeConverter
from conduit.Tree import DataProviderTreeModel, DataProviderTreeView
from conduit.Conflict import ConflictResolver

import conduit.VolumeMonitor as gnomevfs

class GtkView:
    """
    The main conduit window.
    """

    def __init__(self, conduitApplication):
        """
        Constructs the mainwindow. Throws up a splash screen to cover 
        the most time consuming pieces
        """
        gnome.init(conduit.APPNAME, conduit.APPVERSION)
        #FIXME: This causes X errors (async reply??) sometimes in the sync thread???
        gnome.ui.authentication_manager_init()        

        self.conduitApplication = conduitApplication

        #add some additional dirs to the icon theme search path so that
        #modules can provider their own icons
        icon_dirs = [
                    conduit.SHARED_DATA_DIR,
                    conduit.SHARED_MODULE_DIR,
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
        for i in icon_dirs:                    
            gtk.icon_theme_get_default().prepend_search_path(i)
            logd("Adding %s to icon theme search path" % (i))

        self.widgets = gtk.glade.XML(conduit.GLADE_FILE, "MainWindow")
        
        dic = { "on_mainwindow_delete" : self.on_window_closed,
                "on_mainwindow_resized" : self.on_window_resized,
                "on_synchronize_activate" : self.on_synchronize_all_clicked,      
                "on_quit_activate" : self.on_window_closed,
                "on_clear_canvas_activate" : self.on_clear_canvas,
                "on_preferences_activate" : self.on_conduit_preferences,
                "on_about_activate" : self.on_about_conduit,
                "on_save1_activate" : self.save_settings,
                None : None
                }
         
        self.widgets.signal_autoconnect(dic)
        
        #Initialize the mainWindow
        self.mainWindow = self.widgets.get_widget("MainWindow")
        self.mainWindow.hide()
        self.mainWindow.set_title(conduit.APPNAME)
        self.mainWindow.set_position(gtk.WIN_POS_CENTER)
        self.mainWindow.set_icon_from_file(os.path.join(conduit.SHARED_DATA_DIR, "conduit-icon.png"))
        
        #Configure canvas
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.hpane = self.widgets.get_widget("hpaned1")

        #Configure popup menus
        self.canvas_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "ConduitMenu")
        self.item_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "DataProviderMenu") 
        self.canvas_popup_widgets.signal_autoconnect(self)
        self.item_popup_widgets.signal_autoconnect(self)        

        #customize some widgets, connect signals, etc
        self.hpane.set_position(250)
        #start up the canvas
        self.canvas = Canvas()
        self.canvasSW.add(self.canvas)
        #set canvas options
        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)
        #Pass both popups to the canvas
        self.canvas.set_popup_menus( 
                                self.canvas_popup_widgets,
                                self.item_popup_widgets
                                )
        
        # Populate the tree model
        self.dataproviderTreeModel = DataProviderTreeModel() 
        dataproviderScrolledWindow = self.widgets.get_widget("scrolledwindow2")
        self.dataproviderTreeView = DataProviderTreeView(self.dataproviderTreeModel)
        dataproviderScrolledWindow.add(self.dataproviderTreeView)
        dataproviderScrolledWindow.show_all()

        #Set up the expander used for resolving sync conflicts
        self.conflictResolver = ConflictResolver(self.widgets)
        
    def set_model(self, model):
        """
        In conduit the model manages all available dataproviders. It is shared
        between the dbus and the Gtk interface.
        """
        self.moduleManager = model

        #add the dataproviders to the treemodel
        self.dataproviderTreeModel.add_dataproviders(self.moduleManager.get_modules_by_type("source"))
        self.dataproviderTreeModel.add_dataproviders(self.moduleManager.get_modules_by_type("sink"))
        self.dataproviderTreeModel.add_dataproviders(self.moduleManager.get_modules_by_type("twoway"))

        #furthur from this point all dataproviders are loaded in callback as 
        #its the easiest way modules which can be added and removed at runtime (like ipods)
        self.moduleManager.connect("dataprovider-added", self.on_dataprovider_added)
        self.moduleManager.connect("dataprovider-removed", self.on_dataprovider_removed)

        #initialise the Type Converter
        self.type_converter = TypeConverter(self.moduleManager)
        self.canvas.set_type_converter(self.type_converter)
        #initialise the Synchronisation Manager
        self.sync_manager = SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({
                "conflict"  :   conduit.settings.get("twoway_policy_conflict"),
                "deleted"   :   conduit.settings.get("twoway_policy_deleted")}
                )
        self.sync_manager.add_syncworker_callbacks(
                                self.on_sync_started, 
                                self.on_sync_completed, 
                                self.conflictResolver.on_conflict
                                )
        self.dataproviderTreeView.expand_all()

    def on_sync_started(self, thread):
        logd("GUI got sync started")

    def on_sync_completed(self, thread):
        logd("GUI got sync completed")
       
    def on_dataprovider_added(self, loader, dataprovider):
        """
        Called by those classes which only provide dataproviders
        under some conditions that change while the application is running,
        for example an Ipod is plugged in or another conduit instance is
        detected on the network
        """
        if dataprovider.enabled == True:
            self.dataproviderTreeModel.add_dataprovider(dataprovider)
            new = self.moduleManager.get_new_module_instance(dataprovider.get_key())
            self.canvas.check_pending_dataproviders(new)

    def on_dataprovider_removed(self, unloader, dataprovider):
        """
        Called under some conditions that change while application is running,
        for example an iPod is unplugged, or a conduit instance is removed
        from the network
        """
        self.dataproviderTreeModel.remove_dataprovider(dataprovider)
        self.canvas.make_pending_dataproviders(dataprovider)

    def on_synchronize_all_clicked(self, widget):
        """
        Synchronize all valid conduits on the canvas
        """
        for conduit in self.canvas.get_sync_set():
            if conduit.datasource is not None and len(conduit.datasinks) > 0:
                self.sync_manager.sync_conduit(conduit)
            else:
                log("Conduit must have a datasource and a datasink")        

    def on_delete_group_clicked(self, widget):
        """
        Delete a conduit and all its associated dataproviders
        """
        self.canvas.delete_conduit(self.canvas.selected_conduit)

    def on_refresh_group_clicked(self, widget):
        """
        Call the initialize method on all dataproviders in the conduit
        """
        if self.canvas.selected_conduit.datasource is not None and len(self.canvas.selected_conduit.datasinks) > 0:
            self.sync_manager.refresh_conduit(self.canvas.selected_conduit)
        else:
            log("Conduit must have a datasource and a datasink")
    
    def on_synchronize_group_clicked(self, widget):
        """
        Synchronize the selected conduit
        """
        if self.canvas.selected_conduit.datasource is not None and len(self.canvas.selected_conduit.datasinks) > 0:
            self.sync_manager.sync_conduit(self.canvas.selected_conduit)
        else:
            log("Conduit must have a datasource and a datasink")
        
    def on_delete_item_clicked(self, widget):
        """
        delete item
        """
        dp = self.canvas.selected_dataprovider_wrapper
        for c in self.canvas.conduits:
            if c.has_dataprovider(dp):
                c.delete_dataprovider_from_conduit(dp)
                
    def on_configure_item_clicked(self, widget):
        """
        Calls the C{configure(window)} method on the selected dataprovider
        """
        
        dp = self.canvas.selected_dataprovider_wrapper.module
        log("Configuring %s" % dp)
        #May block
        dp.configure(self.mainWindow)

    def on_refresh_item_clicked(self, widget):
        """
        Calls the initialize method on the selected dataprovider
        @todo: Delete this is it does not operate async
        """
        from conduit.DataProvider import STATUS_DONE_REFRESH_OK
        log(
                    "Refreshing %s (FIXME: this blocks and will be deleted)" % \
                    self.canvas.selected_dataprovider_wrapper.get_UID()
                    )
        self.canvas.selected_dataprovider_wrapper.module.refresh()
        self.canvas.selected_dataprovider_wrapper.module.set_status(STATUS_DONE_REFRESH_OK)

    def on_clear_canvas(self, widget):
        """
        Clear the canvas and start a new sync set
        """
        #FIXME: Why does this need to be called in a loop?
        while len(self.canvas.get_sync_set()) > 0:
            for c in self.canvas.get_sync_set():
                self.canvas.delete_conduit(c)
    
    def on_conduit_preferences(self, widget):
        """
        Show the properties of the current sync set (status, conflicts, etc
        Edit the sync specific properties
        """
        def restore_policy_state(policy, ask_rb, replace_rb, skip_rb):
            pref = conduit.settings.get("twoway_policy_%s" % policy)
            if pref == "skip":
                skip_rb.set_active(True)
            elif pref == "replace":
                replace_rb.set_active(True)
            else:
                ask_rb.set_active(True)

        def save_policy_state(policy, ask_rb, replace_rb, skip_rb):
            if skip_rb.get_active() == True:
                i = "skip"
            elif replace_rb.get_active() == True:
                i = "replace"
            else:            
                i = "ask"
            conduit.settings.set("twoway_policy_%s" % policy, i)
            return i

        #Build some liststores to display
        convertables = self.type_converter.get_convertables_descriptive_list()
        converterListStore = gtk.ListStore( str )
        for i in convertables:
            converterListStore.append( [i] )
        dataProviderListStore = gtk.ListStore( str, bool )
        for i in self.moduleManager.get_modules_by_type("sink"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.get_in_type(), i.get_out_type()), i.enabled))
        for i in self.moduleManager.get_modules_by_type("source"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.get_in_type(), i.get_out_type()), i.enabled))
        for i in self.moduleManager.get_modules_by_type("twoway"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.get_in_type(), i.get_out_type()), i.enabled))

        #construct the dialog
        tree = gtk.glade.XML(conduit.GLADE_FILE, "PreferencesDialog")
        #Show the DB contents to help debugging
        if conduit.IS_DEVELOPMENT_VERSION:
            notebook = tree.get_widget("prop_notebook")
            debugText = conduit.mappingDB.debug()
            textView = gtk.TextView()
            textView.set_editable(False)
            textView.get_buffer().set_text(debugText)
            sw = gtk.ScrolledWindow()
            sw.add(textView)
            notebook.append_page(sw,gtk.Label('Mapping DB'))
            notebook.show_all()
        
        converterTreeView = tree.get_widget("dataConversionsTreeView")
        converterTreeView.set_model(converterListStore)
        converterTreeView.append_column(gtk.TreeViewColumn('Conversions Available', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )
        dataproviderTreeView = tree.get_widget("dataProvidersTreeView")
        dataproviderTreeView.set_model(dataProviderListStore)
        dataproviderTreeView.append_column(gtk.TreeViewColumn('Name', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )                                                   
        dataproviderTreeView.append_column(gtk.TreeViewColumn('Enabled', 
                                        gtk.CellRendererToggle(), 
                                        active=1)
                                        )                                        
                                        
        #fill out the configuration tab
        removable_devices_check = tree.get_widget("removable_devices_check")
        removable_devices_check.set_active(conduit.settings.get("enable_removable_devices"))
        save_settings_check = tree.get_widget("save_settings_check")
        save_settings_check.set_active(conduit.settings.get("save_on_exit"))
        status_icon_check = tree.get_widget("status_icon_check")
        status_icon_check.set_active(conduit.settings.get("show_status_icon")) 

        #get the radiobuttons where the user sets their policy
        conflict_ask_rb = tree.get_widget("conflict_ask_rb")
        conflict_replace_rb = tree.get_widget("conflict_replace_rb")
        conflict_skip_rb = tree.get_widget("conflict_skip_rb")
        deleted_ask_rb = tree.get_widget("deleted_ask_rb")
        deleted_replace_rb = tree.get_widget("deleted_replace_rb")
        deleted_skip_rb = tree.get_widget("deleted_skip_rb")
        #set initial conditions        
        restore_policy_state("conflict", conflict_ask_rb, conflict_replace_rb, conflict_skip_rb)
        restore_policy_state("deleted", deleted_ask_rb, deleted_replace_rb, deleted_skip_rb)
                                        
        #Show the dialog
        dialog = tree.get_widget("PreferencesDialog")
        dialog.set_transient_for(self.mainWindow)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            conduit.settings.set("save_on_exit", save_settings_check.get_active())
            conduit.settings.set("show_status_icon", status_icon_check.get_active())
            policy = {}
            policy["conflict"] = save_policy_state("conflict", conflict_ask_rb, conflict_replace_rb, conflict_skip_rb)
            policy["deleted"] = save_policy_state("deleted", deleted_ask_rb, deleted_replace_rb, deleted_skip_rb)
            self.sync_manager.set_twoway_policy(policy)
        dialog.destroy()                


    def on_about_conduit(self, widget):
        """
        Display about dialog
        """
        dialog = ConduitAboutDialog()
        dialog.set_transient_for(self.mainWindow)
        dialog.run()
        dialog.destroy()

    def on_window_closed(self, widget, event=None):
        """
        Check if there are any synchronizations currently in progress and
        ask the user if they wish to cancel them
        """
        busy = False
        quit = False
        for c in self.canvas.get_sync_set(): 
            if c.is_busy():
                busy = True
               
        if busy:       
            dialog = gtk.MessageDialog(
                            self.mainWindow,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_QUESTION,
                            gtk.BUTTONS_YES_NO,_("Synchronization in progress. Do you want to cancel it?")
                            )
            response = dialog.run()
            if response == gtk.RESPONSE_YES:
                quit = True
            else:
                #Dont exit
                dialog.destroy()
                return True
        else:
            quit = True
            
        #OK, if we have decided to quit then call quit on the 
        #DBus interface which will tidy up any pending running
        #non gui tasks
        if quit:
            #FIXME: I want to do this call over DBus but this hangs. Why?
            #sessionBus = dbus.SessionBus()
            #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
            #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
            #conduitApp.Quit()
            self.conduitApplication.Quit()
        
        
    #size-allocate instead of size-request        
    def on_window_resized(self, widget, req):
        """
        Called when window is resized. Tells the canvas to resize itself
        """
        rect = self.canvas.get_allocation()
        self.canvas.resize_canvas(rect.width, rect.height)

        
    def drop_cb(self, wid, context, x, y, time):
        """
        drop cb
        """
        #print "DND DROP = ", context.targets
        self.canvas.drag_get_data(context, context.targets[0], time)
        return True
        
    def drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
        """
        DND
        """
        dataproviderKey = selection.data
        #FIXME: DnD should be cancelled in the Treeview on the drag-begin 
        #signal and NOT here
        if dataproviderKey != "":
            #Add a new instance if the dataprovider to the canvas.
            new = self.moduleManager.get_new_module_instance(dataproviderKey)
            self.canvas.add_dataprovider_to_canvas(dataproviderKey, new, x, y)
        
        context.finish(True, True, etime)
        return
        
    def save_settings(self, widget):
        """
        Saves the application settings to an XML document.
        Saves the GUI settings (window state, position, etc to gconf)
        """
        conduit.settings.save_sync_set( conduit.APPVERSION,
                                        self.canvas.get_sync_set()
                                        )
        #GUI settings
        #print "EXPANDED ROWS - ", self.dataproviderTreeView.get_expanded_rows()
        conduit.settings.set("gui_hpane_postion", self.hpane.get_position())
        conduit.settings.set("gui_window_size", self.mainWindow.get_size())

    def restore_settings(self):
        """
        Restores the application and gui settings
        """
        conduit.settings.restore_sync_set(conduit.APPVERSION, self)
        
        #GUI settings
        self.hpane.set_position(conduit.settings.get("gui_hpane_postion"))
        #print "GUI POSITION - ",conduit.settings.get("gui_window_size")


class SplashScreen:
    """
    Simple splash screen class which shows an image for a predetermined period
    of time or until L{SplashScreen.destroy} is called.
    
    Code adapted from banshee
    """
    DELAY = 1500 #msec
    def __init__(self):        
        """
        Constructor
        """
        #If false the main window should call destroy() to remove the splash
        self.destroyed = True
        
    def show(self):
        """
        Builds the splashscreen and connects the splash window to be destroyed 
        via a timeout callback in L{SplashScreen.DELAY}msec time.

        The splash can also be destroyed manually by the application
        """
        self.wSplash = gtk.Window(gtk.WINDOW_POPUP)
        self.wSplash.set_decorated(False)
        wSplashScreen = gtk.Image()
        wSplashScreen.set_from_file(os.path.join(conduit.SHARED_DATA_DIR,"conduit-splash.png"))

        # Make a pretty frame
        wSplashFrame = gtk.Frame()
        wSplashFrame.set_shadow_type(gtk.SHADOW_OUT)
        wSplashFrame.add(wSplashScreen)
        self.wSplash.add(wSplashFrame)

        # OK throw up the splashscreen
        self.wSplash.set_position(gtk.WIN_POS_CENTER)
        
        #The splash screen is destroyed automatically (via timeout)
        #or when the application is finished loading
        self.destroyed = False

        self.wSplash.show_all()
        # ensure it is rendered immediately
        while gtk.events_pending():
            gtk.main_iteration() 
        # The idle timeout handler to destroy the splashscreen
        gobject.timeout_add(SplashScreen.DELAY,self.destroy)

    def destroy(self):
        """
        Destroys the splashscreen. Can be safely called manually (prior to) 
        or via the timer callback
        """
        if not self.destroyed:
            self.wSplash.destroy()
            self.destroyed = True

class ConduitAboutDialog(gtk.AboutDialog):
    def __init__(self):
        gtk.AboutDialog.__init__(self)
        self.set_name(conduit.APPNAME)
        self.set_version(conduit.APPVERSION)
        self.set_comments("Synchronisation for GNOME")
        self.set_website("http://www.conduit-project.org")
        self.set_authors(["John Stowers", "John Carr"])
        self.set_logo_icon_name("conduit-icon")

class ConduitStatusIcon(gtk.StatusIcon):
    def __init__(self, conduitApplication):
        gtk.StatusIcon.__init__(self)
        self.conduitApplication = conduitApplication
        menu = '''
            <ui>
             <menubar name="Menubar">
              <menu action="Menu">
               <menuitem action="Sync"/>
               <menuitem action="Quit"/>
               <separator/>
               <menuitem action="About"/>
              </menu>
             </menubar>
            </ui>
        '''
        actions = [
            ('Menu',  None, 'Menu'),
            ('Sync', gtk.STOCK_EXECUTE, '_Synchronize', None, 'Synchronize all dataproviders', self.on_synchronize),
            ('Quit', gtk.STOCK_QUIT, '_Quit', None, 'Close Conduit', self.on_quit),
            ('About', gtk.STOCK_ABOUT, '_About', None, 'About Conduit', self.on_about)]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent        
        self.connect('popup-menu', self.on_popup_menu)

        #start with the application icon
        self._reset_states()
        self._go_to_idle_state()
        self.set_tooltip("Conduit")
        self.set_visible(True)

    def _reset_states(self):
        self.running = 0
        self.conflict = False
        self.animated_idx = 0
        self.animated_icons = range(1,8)

    def _go_to_idle_state(self):
        self.set_from_icon_name("conduit-icon")
        self.set_tooltip("Synchronization Complete")

    def _go_to_conflict_state(self):
        self.set_from_icon_name("dialog-error")
        self.set_tooltip("Synchronization Error")

    def _go_to_running_state(self):
        self.set_tooltip("Synchronizing")
        if self.animated_idx == self.animated_icons[-1]:
            self.animated_idx = 1
        else:
            self.animated_idx += 1
        self.set_from_icon_name("conduit-progress-%d" % self.animated_idx)
        if self.running == 0:
            if self.conflict:
                self._go_to_conflict_state()
                self._reset_states()
            else:
                self._go_to_idle_state()
                self._reset_states()

            return False
        else:
            return True

    def on_sync_started(self, thread):
        self.running += 1
        gobject.timeout_add(100, self._go_to_running_state)
        logd("Icon got sync started")

    def on_sync_completed(self, thread):
        self.running -= 1
        logd("Icon got sync completed %s" % self.running)

    def on_sync_conflict(self, thread, *args):
        self.conflict = True
        logd("Icon got sync conflict")

    def on_synchronize(self, data):
        #sessionBus = dbus.SessionBus()
        #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
        #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
        #conduitApp.Synchronize()
        self.conduitApplication.Synchronize()

    def on_popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def on_quit(self, data):
        #sessionBus = dbus.SessionBus()
        #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
        #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
        #conduitApp.Quit()
        self.conduitApplication.Quit()

    def on_about(self, data):
        dialog = ConduitAboutDialog()
        dialog.run()
        dialog.destroy()

class Application(dbus.service.Object):
    def __init__(self):
        """
        Conduit application class

        Parses command line arguments. Shows the main window and 
        enters the gtk mainloop. Sets up the views and models;
        restores application settings, shows the splash screen.

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

        #Default command line values
        if conduit.IS_DEVELOPMENT_VERSION:
            settingsFile = os.path.join(conduit.USER_DIR, "settings-dev.xml")
            dbFile = os.path.join(conduit.USER_DIR, "mapping-dev.db")
        else:
            settingsFile = os.path.join(conduit.USER_DIR, "settings.xml")
            dbFile = os.path.join(conduit.USER_DIR, "mapping.db")

        sessionBus = dbus.SessionBus()
        buildGUI = True
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hs:c", ["help", "settings=", "console"])
            #parse args
            for o, a in opts:
                if o in ("-h", "--help"):
                    self._usage()
                    sys.exit(0)
                if o in ("-s", "--settings"):
                     settingsFile = os.path.join(os.getcwd(), a)
                if o in ("-c", "--console"):
                   buildGUI = False
        except getopt.GetoptError:
            # print help information and exit:
            logw("Unknown command line option")
            self._usage()
            sys.exit(1)

        log("Conduit v%s Installed: %s" % (conduit.APPVERSION, conduit.IS_INSTALLED))
        log("Log Level: %s" % conduit.LOG_LEVEL)
        memstats = conduit.memstats()

        #FIXME: attempt workaround for gnomvefs bug...
        #this shouldn't need to be here, but if we call it after 
        #touching the session bus then nothing will work
        gnomevfs.VolumeMonitor()

        #Make conduit single instance. If conduit is already running then
        #make the original process build or show the gui
        if Utils.dbus_service_available(sessionBus, conduit.DBUS_IFACE):
            log("Conduit is already running")
            obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
            conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
            if buildGUI:
                if conduitApp.HasGUI():
                    conduitApp.ShowGUI()
                else:
                    conduitApp.BuildGUI()
            sys.exit(0)

        # Initialise dbus stuff here as any earlier will cause breakage
        # 1: Outstanding gnomevfs bug!
        # 2: Interferes with Conduit already running check.
        bus_name = dbus.service.BusName(conduit.DBUS_IFACE, bus=sessionBus)
        dbus.service.Object.__init__(self, bus_name, "/activate")

        #Throw up a splash screen ASAP. Dont show if launched via --console.
        if buildGUI:
            self._show_splash()

        #Dynamically load all datasources, datasinks and converters
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            os.path.join(conduit.USER_DIR, "modules")
                            ]
        self.model = ModuleManager(dirs_to_search)

        #The status icon is shared between the GUI and the Dbus iface
        if conduit.settings.get("show_status_icon") == True:
            self.statusIcon = ConduitStatusIcon(self)
           
        #Set up the application wide defaults
        conduit.settings.set_settings_file(settingsFile)
        conduit.mappingDB.open_db(dbFile)

        #Set the view models
        if buildGUI:
            self.BuildGUI()

        #Dbus view...
        if conduit.settings.get("enable_dbus_interface") == True:
            self.dbus = DBusView(self)
            self.dbus.set_model(self.model)

            if self.statusIcon:
                self.dbus.sync_manager.add_syncworker_callbacks(
                                        self.statusIcon.on_sync_started,
                                        self.statusIcon.on_sync_completed,
                                        self.statusIcon.on_sync_conflict
                                        )

        conduit.memstats(memstats)
        gtk.main()

    def _show_splash(self):
        if conduit.settings.get("show_splashscreen") == True:
            self.splash = SplashScreen()
            self.splash.show()

    def _usage(self):
        print """Conduit: Usage
$ %s [OPTIONS]

OPTIONS:
    -h, --help          Print this help notice.
    -c, --console       Launch Conduit with no GUI) (default=no).
    -s, --settings=FILE Override saving conduit settings to FILE""" % sys.argv[0]

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='b')
    def HasGUI(self):
        return self.gui != None

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='')
    def BuildGUI(self):
        #if the gui is build after the splash then show it, even though it
        #will be a shorter period of time because the modules have already 
        #been scanned
        if self.splash == None:
            self._show_splash()

        self.gui = GtkView(self)
        self.gui.set_model(self.model)
        self.gui.canvas.add_welcome_message()
        self.gui.restore_settings()
        self.gui.mainWindow.show_all()

        if self.statusIcon:
            self.gui.sync_manager.add_syncworker_callbacks(
                                    self.statusIcon.on_sync_started,
                                    self.statusIcon.on_sync_completed,
                                    self.statusIcon.on_sync_conflict
                                    )

        if self.splash != None:
            self.splash.destroy()
    
    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='')
    def ShowGUI(self):
        self.gui.mainWindow.present()

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='')
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

        gtk.main_quit()

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='')
    def Synchronize(self):
        if self.gui != None:
            self.gui.on_synchronize_all_clicked(None)
