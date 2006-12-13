"""
Draws the applications main window

Also manages the callbacks from menu and GUI items

Copyright: John Stowers, 2006
License: GPLv2
"""
import gnomevfs
import gobject
import gtk
import gtk.glade
import gnome.ui
import copy
import os.path
from gettext import gettext as _
import elementtree.ElementTree as ET

import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import logging
import conduit
from conduit.DBus import DBusView
from conduit.Module import ModuleManager
from conduit.Canvas import Canvas
from conduit.Synchronization import SyncManager
from conduit.TypeConverter import TypeConverter
from conduit.Tree import DataProviderTreeModel, DataProviderTreeView
from conduit.Conflict import ConflictResolver
from conduit.DBus import dbus_service_available

CONDUIT_DBUS_PATH = "/gui"
CONDUIT_DBUS_IFACE = "org.freedesktop.conduit"

class GtkView(dbus.service.Object):
    """
    The main conduit window.
    """

    def __init__(self):
        """
        Constructs the mainwindow. Throws up a splash screen to cover 
        the most time consuming pieces
        """
        gnome.init(conduit.APPNAME, conduit.APPVERSION)
        #FIXME: This causes X errors (async reply??) sometimes in the sync thread???
        gnome.ui.authentication_manager_init()        
        #Throw up a splash screen ASAP to look pretty (if the user wants) 
        self.splash = SplashScreen()
        if conduit.settings.get("show_splashscreen") == True:
            self.splash.show()

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
            logging.info("Adding %s to icon them search path" % (i))

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
        self.canvas_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "GroupMenu")
        self.item_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "ItemMenu") 
        self.canvas_popup_widgets.signal_autoconnect(self)
        self.item_popup_widgets.signal_autoconnect(self)        

        #customize some widgets, connect signals, etc
        self.hpane.set_position(250)
        #start up the canvas
        self.canvas = Canvas()
        self.canvasSW.add(self.canvas)
        #set canvas options
        self.canvas.disable_two_way_sync(conduit.settings.get("disable_twoway_sync"))
        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)
        #Pass both popups to the canvas
        self.canvas.set_popup_menus( 
                                self.canvas_popup_widgets,
                                self.item_popup_widgets
                                )
        
        # Populate the tree models
        #self.datasink_tm = DataProviderTreeModel()
        self.datasource_tm = DataProviderTreeModel() 
        #sink_scrolled_window = self.widgets.get_widget("scrolledwindow3")
        source_scrolled_window = self.widgets.get_widget("scrolledwindow2")
        #sink_scrolled_window.add(DataProviderTreeView(self.datasink_tm))
        self.datasource_tv = DataProviderTreeView(self.datasource_tm)
        source_scrolled_window.add(self.datasource_tv)
        #sink_scrolled_window.show_all()
        source_scrolled_window.show_all()

        #Set up the expander used for resolving sync conflicts
        self.conflictResolver = ConflictResolver()
        self.widgets.get_widget("conflictScrolledWindow").add(self.conflictResolver.view)

        #Dbus can also be used to control the gui. Useful for 
        #automated testing and activation
        if conduit.settings.get("enable_dbus_interface") == True:
            bus_name = dbus.service.BusName(CONDUIT_DBUS_IFACE, bus=dbus.SessionBus())
            dbus.service.Object.__init__(self, bus_name, CONDUIT_DBUS_PATH)

    def set_model(self, model):
        """
        In conduit the model manages all available dataproviders. It is shared
        between the dbus and the Gtk interface.

        This function
        """
        self.moduleManager = model

        #add the dataproviders to the treemodel
        self.datasource_tm.add_dataproviders(self.moduleManager.get_modules_by_type("source"))
        self.datasource_tm.add_dataproviders(self.moduleManager.get_modules_by_type("sink"))
        #self.datasink_tm.add_dataproviders(self.moduleManager.get_modules_by_type("sink"))
        #furthur from this point all dataproviders are loaded in callback as 
        #its the easiest way modules which can be added and removed at runtime (like ipods)
        self.moduleManager.connect("dataprovider-added", self.on_dataprovider_added)
        self.moduleManager.connect("all-modules-loaded", lambda x: self.datasource_tv.expand_all())

        #initialise the Type Converter
        converters = self.moduleManager.get_modules_by_type("converter")
        self.type_converter = TypeConverter(converters)
        self.canvas.set_type_converter(self.type_converter)
        #initialise the Synchronisation Manager
        self.sync_manager = SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({
                "conflict"  :   conduit.settings.get("twoway_policy_conflict"),
                "missing"   :   conduit.settings.get("twoway_policy_missing")}
                )
        self.sync_manager.set_sync_callbacks(None, self.conflictResolver.on_conflict)
        self.datasource_tv.expand_all()

       
    def on_dataprovider_added(self, loader, dataprovider):
        """
        Called by those classes which only provide dataproviders
        under some conditions that change while the application is running,
        for example an Ipod is plugged in or another conduit instance is
        detected on the network
        """
        if dataprovider.enabled == True:
            #if dataprovider.module_type == "source":
            self.datasource_tm.add_dataprovider(dataprovider)
            #elif dataprovider.module_type == "sink":
            #    self.datasink_tm.add_dataprovider(dataprovider)

    def on_synchronize_all_clicked(self, widget):
        """
        Synchronize all valid conduits on the canvas
        """
        for conduit in self.canvas.get_sync_set():
            if conduit.datasource is not None and len(conduit.datasinks) > 0:
                self.sync_manager.sync_conduit(conduit)
            else:
                logging.info("Conduit must have a datasource and a datasink")        

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
            logging.info("Conduit must have a datasource and a datasink")
    
    def on_synchronize_group_clicked(self, widget):
        """
        Synchronize the selected conduit
        """
        if self.canvas.selected_conduit.datasource is not None and len(self.canvas.selected_conduit.datasinks) > 0:
            self.sync_manager.sync_conduit(self.canvas.selected_conduit)
        else:
            logging.info("Conduit must have a datasource and a datasink")
    	
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
        logging.info("Configuring %s" % dp)
        #May block
        dp.configure(self.mainWindow)

    def on_refresh_item_clicked(self, widget):
        """
        Calls the initialize method on the selected dataprovider
        @todo: Delete this is it does not operate async
        """
        logging.info(
                    "Refreshing %s (FIXME: this blocks and will be deleted)" % \
                    self.canvas.selected_dataprovider_wrapper.get_unique_identifier()
                    )
        self.canvas.selected_dataprovider_wrapper.module.refresh()

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
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.in_type, i.out_type), i.enabled))
        for i in self.moduleManager.get_modules_by_type("source"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.in_type, i.out_type), i.enabled))
           
        #construct the dialog
        tree = gtk.glade.XML(conduit.GLADE_FILE, "PreferencesDialog")
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
        use_two_way_sync_check = tree.get_widget("use_two_way_sync_check")
        use_two_way_sync_check.set_active(conduit.settings.get("disable_twoway_sync")) 

        #get the radiobuttons where the user sets their policy
        conflict_ask_rb = tree.get_widget("conflict_ask_rb")
        conflict_replace_rb = tree.get_widget("conflict_replace_rb")
        conflict_skip_rb = tree.get_widget("conflict_skip_rb")
        missing_ask_rb = tree.get_widget("missing_ask_rb")
        missing_replace_rb = tree.get_widget("missing_replace_rb")
        missing_skip_rb = tree.get_widget("missing_skip_rb")
        #set initial conditions        
        restore_policy_state("conflict", conflict_ask_rb, conflict_replace_rb, conflict_skip_rb)
        restore_policy_state("missing", missing_ask_rb, missing_replace_rb, missing_skip_rb)
                                        
        #Show the dialog
        dialog = tree.get_widget("PreferencesDialog")
        dialog.set_transient_for(self.mainWindow)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            disable = use_two_way_sync_check.get_active()
            conduit.settings.set("save_on_exit", save_settings_check.get_active())
            conduit.settings.set("disable_twoway_sync", disable)
            #FIXME: Once the 2way stuff is confirmed, this setting will be removed
            #From the prefs, and be managed entirely from the right click conduit menu
            self.canvas.disable_two_way_sync(disable)
            #Save the users two way sync policy
            policy = {}
            policy["conflict"] = save_policy_state("conflict", conflict_ask_rb, conflict_replace_rb, conflict_skip_rb)
            policy["missing"] = save_policy_state("missing", missing_ask_rb, missing_replace_rb, missing_skip_rb)
            self.sync_manager.set_twoway_policy(policy)
        dialog.destroy()                


    def on_about_conduit(self, widget):
        """
        Display about dialog
        """
        aboutTree = gtk.glade.XML(conduit.GLADE_FILE, "AboutDialog")
        dlg = aboutTree.get_widget("AboutDialog")
        dlg.set_name(conduit.APPNAME)
        dlg.set_version(conduit.APPVERSION)
        dlg.set_transient_for(self.mainWindow)
        dlg.connect('response', lambda widget, response: widget.destroy())
        #dlg.set_icon(self.icon)        

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
                logging.info("Stopping all synchronization threads")
                self.sync_manager.cancel_all()
                quit = True
            else:
                #Dont exit
                dialog.destroy()
                return True
        else:
            quit = True
            
        #OK, if we have decided to quit then perform any cleanup tasks
        if quit:
            if conduit.settings.get("save_on_exit") == True:
                conduit.settings.save_sync_set(conduit.APPVERSION,self.canvas.get_sync_set())
            gtk.main_quit()
        
        
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
        moduleClassName = selection.data
        #FIXME: DnD should be cancelled in the Treeview on the drag-begin 
        #signal and NOT here
        if moduleClassName != "ImACategoryNotADataprovider":
            #logging.info("DND RX = %s" % (module_name))        
            #Add a new instance if the dataprovider to the canvas. It is up to the
            #canvas to decide if multiple instances of the specific provider are allowed
            new = self.moduleManager.get_new_module_instance(moduleClassName)
            if new != None:
                self.canvas.add_dataprovider_to_canvas(new, x, y)
        
        context.finish(True, True, etime)
        return
        
    def save_settings(self, widget):
        """
        Saves the application settings to an XML document
        """
        conduit.settings.save_sync_set( conduit.APPVERSION,
                                        self.canvas.get_sync_set()
                                        )

    #---------------------------------------------------------------------------
    # DBUS METHODS (follow DBus naming conventions
    #
    # Example: dbus-send --session --dest=org.freedesktop.conduit \
    #           --print-reply /gui org.freedesktop.conduit.Ping
    #---------------------------------------------------------------------------
    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Ping(self):
        """
        Test method to check the DBus interface is working
        """
        return "GtkView Pong"

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Present(self):
        """
        Test method to check the DBus interface is working
        """
        self.mainWindow.present()

    
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

#FIXME: Make this into a proper class used just for managing single instance
#and command line usage.
#0) Make into proper class. Most of whats below goes into __init__
#1) Make it its own dbus iface at the /activate path
#2) It should have single method - Activate()
#3) Remeber the case where the user has started it via --console (or DBus activation)
#   In that case GTkView will have to be constructed before being presented
def conduit_main():
    """
    Conduit main initialization function

    Parses command line arguments. Shows the main window and 
    enters the gtk mainloop. Sets up the views and models;
    restores application settings, shows a welcome message and
    closes the splash screen
    """
    memstats = conduit.memstats()
    import getopt, sys
    #Default command line values
    settingsFile = os.path.join(conduit.USER_DIR, "settings.xml")
    useGUI = True
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:c", ["help", "settings=", "console"])
        #parse args
        for o, a in opts:
            if o in ("-h", "--help"):
                print "./%s [--help] [--settings=path_to_settings_file] [--console]" % sys.argv[0]
                sys.exit(0)
            if o in ("-s", "--settings"):
                settingsFile = os.path.join(os.getcwd(), a)
            if o in ("-c", "--console"):
                useGUI = False
    except getopt.GetoptError:
        # print help information and exit:
        logging.warn("Unknown command line option")
        pass

    #Make conduit single instance. If it is already running then present it
    #to the user
    if dbus_service_available(dbus.SessionBus(), CONDUIT_DBUS_IFACE):
        logging.info("Conduit is already running")
        bus = dbus.SessionBus()
        obj = bus.get_object(CONDUIT_DBUS_IFACE, CONDUIT_DBUS_PATH)
        iface = dbus.Interface(obj, CONDUIT_DBUS_IFACE)
        iface.Present()
        sys.exit(0)
        
    #Draw the GUI asap so that the user sees the splash screen
    if useGUI:
        gtkView = GtkView()

    #Dynamically load all datasources, datasinks and converters
    dirs_to_search =    [
                        os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                        os.path.join(conduit.USER_DIR, "modules")
                        ]
    model = ModuleManager(dirs_to_search)
    #Unfortunately to be able to restore sync settings all modules must be loaded
    #in this blocking function.
    model.load_static_modules()

    #Set the view models
    #gtkView...
    if useGUI:
        gtkView.set_model(model)
        conduit.settings.set_settings_file(settingsFile)
        conduit.settings.restore_sync_set(conduit.APPVERSION, gtkView)
    #Dbus view...
    if conduit.settings.get("enable_dbus_interface") == True:
        dbusView = DBusView()
        dbusView.set_model(model)

    #Start the application
    if useGUI:
        gtkView.canvas.add_welcome_message()
        gtkView.splash.destroy()
        gtkView.mainWindow.show_all()
    memstats = conduit.memstats(memstats)
    gtk.main()
