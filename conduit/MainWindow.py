"""
Draws the applications main window

Also manages the callbacks from menu and GUI items

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject
import gtk
import gtk.glade
import gnome.ui
import copy
import os.path
from gettext import gettext as _

import logging
import conduit
import conduit.Canvas as Canvas
import conduit.Module as Module
import conduit.Synchronization as Synchronization
import conduit.TypeConverter as TypeConverter
import conduit.DataProvider as DataProvider

import conduit.Exceptions as Exceptions

import threading

class MainWindow:
    """
    The main conduit class.
    """

    def __init__(self):
        gnome.init(conduit.APPNAME, conduit.APPVERSION)
        #add some additional dirs to the icon theme search path so that
        #modules can provider their own icons
        icon_dirs = [
                    conduit.SHARED_DATA_DIR,
                    conduit.SHARED_MODULE_DIR,
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.abspath(os.path.expanduser(conduit.USER_MODULE_DIR))
                    ]
        for i in icon_dirs:                    
            gtk.icon_theme_get_default().prepend_search_path(i)
            logging.info("Adding %s to icon them search path" % (i))

        self.widgets = gtk.glade.XML(conduit.GLADE_FILE, "window1")
        
        dic = { "on_window1_destroy" : self.on_window_closed,
                "on_window1_resized" : self.on_window_resized,
                "on_open_activate" : self.on_open_sync_set,
                "on_save_activate" : self.on_save_sync_set,
                "on_save_as_activate" : self.on_save_as_sync_set,
                "on_new_activate" : self.on_new_sync_set,
                "on_synchronize_activate" : self.on_synchronize_all_clicked,      
                "on_quit_activate" : self.on_window_closed,
                "on_clear_activate" : self.on_clear_sync_set,
                "on_properties_activate" : self.on_sync_properties,
                "on_preferences_activate" : self.on_conduit_preferences,
                "on_about_activate" : self.on_about_conduit,
                "on_hpane_move_handle" : self.on_hpane_move_handle,
                None : None
                }
         
        self.widgets.signal_autoconnect(dic)
        
        #get some widget references
        self.mainWindow = self.widgets.get_widget("window1")
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.hpane = self.widgets.get_widget("hpaned1")

        self.canvas_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "menu1")
        self.item_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "menu2") 


        #customize some widgets, connect signals, etc
        self.mainWindow.set_title(conduit.APPNAME)
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
                                self.canvas_popup_widgets.get_widget("menu1"),
                                self.item_popup_widgets.get_widget("menu2")
                                )
        
        #Dynamically load all datasources, datasinks and converters (Python is COOL!)
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            conduit.USER_MODULE_DIR
                            ]
        self.modules = Module.ModuleLoader(dirs_to_search)
        #@todo: Make this asyc
        self.modules.load_all_modules()
        self.datasink_modules = self.modules.get_modules_by_type ("sink")
        self.datasource_modules = self.modules.get_modules_by_type ("source")
        self.converter_modules = self.modules.get_modules_by_type ("converter")
                        
        # Populate the tree and list models
        #FIXME: how many of these really need to be kep around in self aye??
        self.datasink_tm = DataProvider.DataProviderTreeModel(self.datasink_modules)
        self.datasink_tv = DataProvider.DataProviderTreeView(self.datasink_tm)
        self.datasource_tm = DataProvider.DataProviderTreeModel(self.datasource_modules)
        self.datasource_tv = DataProvider.DataProviderTreeView(self.datasource_tm)
        self.sink_scrolled_window = self.widgets.get_widget("scrolledwindow3")
        self.source_scrolled_window = self.widgets.get_widget("scrolledwindow2")
        self.sink_scrolled_window.add(self.datasink_tv)
        self.source_scrolled_window.add(self.datasource_tv)
        self.sink_scrolled_window.show_all()
        self.source_scrolled_window.show_all()


        #initialise the Type Converter
        converters = self.modules.get_modules_by_type("converter")
        self.type_converter = TypeConverter(converters)
        #initialise the Synchronisation Manager
        self.sync_manager = Synchronization.SyncManager(self.type_converter)
        
        #dic = gtk.icon_theme_get_default().list_icons()
        #for d in dic:
        #    print d


    # callbacks.
    def on_synchronize_all_clicked(self, widget):
        """
        Synchronize all valid conduits on the canvas
        """
        sync_set = self.canvas.get_sync_set()
        for conduit in sync_set:
            if conduit.datasource is not None and len(conduit.datasinks) > 0:
                self.sync_manager.sync_conduit(conduit)
            else:
                logging.info("Conduit must have a datasource and a datasink")        

        
    def on_delete_group_clicked(self, widget):
        """
        sync
        """
        logging.debug("Delete Group") 

    def on_refresh_group_clicked(self, widget):
        """
        sync
        """
        logging.debug("Refresh Group")    
    
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
        logging.debug("Delete Item")
        
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
        Calls the 
        """
        dp = self.canvas.selected_dataprovider_wrapper.module
        logging.info("Refreshing %s" % dp)

        dp.initialize()

    def on_synchronize_item_clicked(self, widget):
        """
        paste item
        """
        logging.debug("Synchronize Item")
        
    def on_open_sync_set(self, widget):
        """
        Open a saved sync set from disk
        """
        print "open sync set"
        
    def on_save_sync_set(self, widget):
        """
        Save the current sync settings to disk
        """
        print "save sync set"
        
    def on_save_as_sync_set(self, widget):
        """
        Save a copy of the current sync settings to disk
        """
        print "saveas sync set"
        
    def on_new_sync_set(self, widget):
        """
        Clear the canvas and start a new sync set
        """
        print "new sync set"
        
    def on_clear_sync_set(self, widget):
        """
        Clear the canvas and start a new sync set
        """
        print "clear sync set"
    
    def on_sync_properties(self, widget):
        """
        Show the properties of the current sync set (status, conflicts, etc
        Edit the sync specific properties
        """
        #Build some liststores to display
        convertables = self.type_converter.get_convertables_descriptive_list()
        converterListStore = gtk.ListStore( str )
        for i in convertables:
            converterListStore.append( [i] )
        dataProviderListStore = gtk.ListStore( str )
        for i in self.datasink_modules:
            dataProviderListStore.append(["%s %s (type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.in_type, i.out_type)])
        for i in self.datasource_modules:
            dataProviderListStore.append(["%s %s (type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.in_type, i.out_type)])
           
        #construct the dialog
        tree = gtk.glade.XML(conduit.GLADE_FILE, "PropertiesDialog")
        dataproviderTreeView = tree.get_widget("dataProvidersTreeView")
        dataproviderTreeView.set_model(dataProviderListStore)
        dataproviderTreeView.append_column(gtk.TreeViewColumn('Name', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )                                                   
        converterTreeView = tree.get_widget("dataConversionsTreeView")
        converterTreeView.set_model(converterListStore)
        converterTreeView.append_column(gtk.TreeViewColumn('Name', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )
                                        
                                        
        #Show the dialog
        dialog = tree.get_widget("PropertiesDialog")
        dialog.set_transient_for(self.mainWindow)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            logging.debug("OK")
            pass
        elif response == gtk.RESPONSE_CANCEL:
            logging.debug("CANCEL")        
            pass
        else:
            logging.debug("DUNNO")
        dialog.destroy()                


        
    def on_conduit_preferences(self, widget):
        """
        Edit the application wide preferences
        """
        print "application preferences"

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

    def on_window_closed(self, widget):
        """
        Kills the app and cleans up
        """
        gtk.main_quit()
        
    #TODO: If dynamic resizing causes too much CPU usage connect to 
    #size-allocate instead of size-request
    def on_hpane_move_handle(self, widget, req):
        #print "pane moved ", widget.get_position()
        pass
        
    #size-allocate instead of size-request        
    def on_window_resized(self, widget, req):
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
        module_name = selection.data
        logging.info("DND RX = %s" % (module_name))        
        #Add a new instance if the dataprovider to the canvas. It is up to the
        #canvas to decide if multiple instances of the specific provider are allowed
        new = self.modules.get_new_instance_module_named(module_name)
        self.canvas.add_module_to_canvas(new, x, y)
        
        context.finish(True, True, etime)
        return        

    def __main__(self):
        gtk.main()    	
