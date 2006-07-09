import gobject
import gtk
import gtk.glade
import gnome.ui
import copy
import os.path

import logging
import conduit
import conduit.ConduitEditorCanvas as ConduitEditorCanvas
import conduit.ModuleManager as ModuleManager
import conduit.SyncManager as SyncManager
import conduit.TypeConverter as TypeConverter

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
                    os.path.join(conduit.SHARED_MODULE_DIR,"datatypes"),
                    os.path.abspath(os.path.expanduser(conduit.USER_MODULE_DIR))
                    ]
        for i in icon_dirs:                    
            gtk.icon_theme_get_default().prepend_search_path(i)
            logging.info("Adding %s to icon them search path" % (i))

        self.widgets = gtk.glade.XML(conduit.GLADE_FILE, "window1")
        
        dic = { "on_window1_destroy" : self.on_window_closed,
                "on_window1_resized" : self.on_window_resized,
                "on_synchronizebutton_clicked" : self.on_synchronize_clicked,
                "on_open_activate" : self.on_open_sync_set,
                "on_save_activate" : self.on_save_sync_set,
                "on_save_as_activate" : self.on_save_as_sync_set,
                "on_new_activate" : self.on_new_sync_set,
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
        self.mainwindow = self.widgets.get_widget("window1")
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.hpane = self.widgets.get_widget("hpaned1")

        self.canvas_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "menu1")
        self.item_popup_widgets = gtk.glade.XML(conduit.GLADE_FILE, "menu2") 


        #customize some widgets, connect signals, etc
        self.mainwindow.set_title(conduit.APPNAME)
        self.hpane.set_position(250)
        #start up the canvas
        self.canvas = ConduitEditorCanvas.ConduitEditorCanvas()
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
        
        #Dynamically load all datasources, datasinks and datatypes (Python is COOL!)
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"datatypes"),
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            conduit.USER_MODULE_DIR
                            ]
        self.modules = ModuleManager.ModuleManager(dirs_to_search)
        
        #dic = gtk.icon_theme_get_default().list_icons()
        #for d in dic:
        #    print d
                        
        if False:#conduit.DEBUG:
            datasink_modules = self.modules.module_loader.get_modules ("sink")
            datasource_modules = self.modules.module_loader.get_modules ("source")
            datatypes = self.modules.module_loader.get_modules ("datatype")
            print "SINKS"
            for q in datasink_modules:
                print "Name = '%s' Description = '%s' Type = '%s' Category = '%s'" % (q.name, q.description, q.module_type, q.category)
                print "Raw ", q.module
            
            print "SOURCES"
            for q in datasource_modules:
                print "Name = '%s' Description = '%s' Type = '%s' Category = '%s'" % (q.name, q.description, q.module_type, q.category)
                print "Raw ", q.module
            
            print "TYPES"
            for q in datatypes:
                print "Name = '%s' Description = '%s' Type = '%s' Category = '%s'" % (q.name, q.description, q.module_type, q.category)
                print "Raw ", q.module
                
        
        # Populate the tree and list models
        self.source_scrolled_window = self.widgets.get_widget("scrolledwindow2")
        self.sink_scrolled_window = self.widgets.get_widget("scrolledwindow3")
        self.source_scrolled_window.add(self.modules.get_treeview("source"))
        self.sink_scrolled_window.add(self.modules.get_treeview("sink"))
        self.source_scrolled_window.show_all()
        self.sink_scrolled_window.show_all()
        
        #initialise the Synchronisation Manager
        self.sync_manager = SyncManager()
        #initialise the Type Converter
        datatypes = self.modules.module_loader.get_modules ("datatype")
        self.type_converter = TypeConverter(datatypes)
        self.type_converter.print_convertables()

    # callbacks.
    def on_synchronize_clicked(self, widget):
        """
        sync
        """
        sync_set = self.canvas.get_sync_set()
        logging.debug(sync_set)
    	
    def on_cut_item_clicked(self, widget):
        """
        cut item
        """
        print "cut item"
        
    def on_copy_item_clicked(self, widget):
        """
        copy item
        """
        print "copy item"
        
    def on_paste_item_clicked(self, widget):
        """
        paste item
        """
        print "paste item"
        
    def on_configure_item_clicked(self, widget):
        """
        paste item
        """
        print "configure item"
        
    def on_synchronize_item_clicked(self, widget):
        """
        paste item
        """
        print "synchronize item"
        
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
        print "sync properties"
        
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
        dlg.set_transient_for(self.mainwindow)
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
        #ADD That sausage to the canvas
        m = self.modules.get_module(module_name)
        self.canvas.add_module_to_canvas(m, x, y)
        
        context.finish(True, True, etime)
        return        

    def __main__(self):
        gtk.main()    	
