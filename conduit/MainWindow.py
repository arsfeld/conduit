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

import logging
import conduit
import conduit.Canvas as Canvas
import conduit.Module as Module
import conduit.Synchronization as Synchronization
import conduit.TypeConverter as TypeConverter
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions

class MainWindow:
    """
    The main conduit class.
    """

    def __init__(self):
        """
        Constructs the mainwindow. Throws up a splash screen to cover 
        the most time consuming pieces
        """
        gnome.init(conduit.APPNAME, conduit.APPVERSION)
        #FIXME: This causes X errors (async reply??) sometimes in the sync thread???
        gnome.ui.authentication_manager_init()        
        #Throw up a splash screen ASAP to look pretty
        #FIXME: The only thing I should do before showing the splash screen
        #is to load the app settings, (like the window position which is
        #going to be used to position the splash)
        self.splash = SplashScreen()
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
        
        #Configure canvas and canvas menus
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.hpane = self.widgets.get_widget("hpaned1")
        self.canvas_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "GroupMenu")
        self.item_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "ItemMenu") 

        #customize some widgets, connect signals, etc
        self.hpane.set_position(250)
        #start up the canvas
        self.canvas = Canvas.Canvas()
        self.canvasSW.add(self.canvas)
        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)
        #Set up the popup widgets
        self.canvas_popup_widgets.signal_autoconnect(self)
        self.item_popup_widgets.signal_autoconnect(self)        
        #Pass both popups to the canvas
        self.canvas.set_popup_menus( 
                                self.canvas_popup_widgets.get_widget("GroupMenu"),
                                self.item_popup_widgets.get_widget("ItemMenu")
                                )
        
        #Dynamically load all datasources, datasinks and converters (Python is COOL!)
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            os.path.join(conduit.USER_DIR, "modules")
                            ]
        self.modules = Module.ModuleLoader(dirs_to_search)
        #self.modules.connect("all-modules-loaded", self.on_all_modules_loaded)
        #self.modules.connect("module-loaded", self.on_module_loaded)        
        self.modules.load_all_modules()
        self.datasink_modules = self.modules.get_modules_by_type ("sink")
        self.datasource_modules = self.modules.get_modules_by_type ("source")
        self.converter_modules = self.modules.get_modules_by_type ("converter")
                        
        # Populate the tree and list models
        if conduit.settings.get("use_treeview") == True:
            datasink_tm = DataProvider.DataProviderTreeModel(self.datasink_modules)
            datasource_tm = DataProvider.DataProviderTreeModel(self.datasource_modules) 
        else:
            datasink_tm = DataProvider.DataProviderListModel(self.datasink_modules)
            datasource_tm = DataProvider.DataProviderListModel(self.datasource_modules) 
        
        datasink_tv = DataProvider.DataProviderTreeView(datasink_tm)
        datasource_tv = DataProvider.DataProviderTreeView(datasource_tm)
        sink_scrolled_window = self.widgets.get_widget("scrolledwindow3")
        source_scrolled_window = self.widgets.get_widget("scrolledwindow2")
        sink_scrolled_window.add(datasink_tv)
        source_scrolled_window.add(datasource_tv)
        sink_scrolled_window.show_all()
        source_scrolled_window.show_all()

        #initialise the Type Converter
        converters = self.modules.get_modules_by_type("converter")
        self.type_converter = TypeConverter(converters)
        self.canvas.set_type_converter(self.type_converter)
        #initialise the Synchronisation Manager
        self.sync_manager = Synchronization.SyncManager(self.type_converter)
        
    # callbacks.
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
        #Build some liststores to display
        convertables = self.type_converter.get_convertables_descriptive_list()
        converterListStore = gtk.ListStore( str )
        for i in convertables:
            converterListStore.append( [i] )
        dataProviderListStore = gtk.ListStore( str, bool )
        for i in self.datasink_modules:
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.in_type, i.out_type), i.enabled))
        for i in self.datasource_modules:
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
        save_settings_check = tree.get_widget("save_settings_check")
        save_settings_check.set_active(conduit.settings.get("save_on_exit"))
        use_treeview_check = tree.get_widget("use_treeview_check")
        use_treeview_check.set_active(conduit.settings.get("use_treeview"))                            
                                        
        #Show the dialog
        dialog = tree.get_widget("PreferencesDialog")
        dialog.set_transient_for(self.mainWindow)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            conduit.settings.set("save_on_exit", save_settings_check.get_active())
            conduit.settings.set("use_treeview", use_treeview_check.get_active())
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
            new = self.modules.get_new_instance_module_named(moduleClassName)
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

    def __main__(self):
        """
        Shows the main window and enters the gtk mainloop
        
        Restores application settings, shows a welcome message and
        closes the splash screen
        """
        self.mainWindow.show_all()
        conduit.settings.restore_sync_set(conduit.APPVERSION,self)
        self.canvas.add_welcome_message()
        self.splash.destroy()
        gtk.main()
        
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
        
        Also connects the splash window to be destroyed via a timeout
        callback in L{SplashScreen.DELAY}msec time
        """
        self.wSplash = gtk.Window(gtk.WINDOW_POPUP )
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
