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
                    os.path.abspath(os.path.expanduser(conduit.USER_MODULE_DIR))
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
                "on_loaded_modules_activate" : self.on_loaded_modules,
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
                            conduit.USER_MODULE_DIR
                            ]
        self.modules = Module.ModuleLoader(dirs_to_search)
        #self.modules.connect("all-modules-loaded", self.on_all_modules_loaded)
        #self.modules.connect("module-loaded", self.on_module_loaded)        
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
        self.canvas.set_type_converter(self.type_converter)
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
        dp = self.canvas.selected_dataprovider_wrapper.module
        dp.refresh()

    def on_clear_canvas(self, widget):
        """
        Clear the canvas and start a new sync set
        """
        logging.debug("clear canvas")
    
    def on_loaded_modules(self, widget):
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
        tree = gtk.glade.XML(conduit.GLADE_FILE, "LoadedModulesDialog")
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
        dialog = tree.get_widget("LoadedModulesDialog")
        dialog.set_transient_for(self.mainWindow)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            pass
        dialog.destroy()                


    def on_conduit_preferences(self, widget):
        """
        Edit the application wide preferences
        """
        logging.debug("application preferences")

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
                gtk.main_quit()
            else:
                #Dont exit
                dialog.destroy()
                return True
        else:
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
        module_name = selection.data
        #FIXME: DnD should be cancelled in the Treeview on the drag-begin 
        #signal and NOT here
        if module_name != "ImACategoryNotADataprovider":
            #logging.info("DND RX = %s" % (module_name))        
            #Add a new instance if the dataprovider to the canvas. It is up to the
            #canvas to decide if multiple instances of the specific provider are allowed
            new = self.modules.get_new_instance_module_named(module_name)
            self.canvas.add_dataprovider_to_canvas(new, x, y)
        
        context.finish(True, True, etime)
        return
        
    def save_settings(self, widget):
        """
        Saves the application settings to an XML document
        """
        import conduit
        from xml.dom.minidom import Document
        #Build the application settings xml document
        doc = Document()
        rootxml = doc.createElement("conduit-application")
        rootxml.setAttribute("version", conduit.APPVERSION)
        doc.appendChild(rootxml)
        
        #Store the conduits
        for conduit in self.canvas.get_sync_set():
            conduitxml = doc.createElement("conduit")
            #First store conduit specific settings
            x,y,w,h = conduit.get_conduit_dimensions()
            conduitxml.setAttribute("x",str(x))
            conduitxml.setAttribute("y",str(y))
            conduitxml.setAttribute("w",str(w))
            conduitxml.setAttribute("h",str(h))
            rootxml.appendChild(conduitxml)
            
            #Store the source
            source = conduit.datasource
            sourcexml = doc.createElement("datasource")
            sourcexml.setAttribute("classname", source.classname)
            conduitxml.appendChild(sourcexml)
            #Store source settings
            configurations = source.module.get_configuration()
            #logging.debug("Source Settings %s" % configurations)
            for config in configurations:
                configxml = doc.createElement(str(config))
                configxml.appendChild(doc.createTextNode(str(configurations[config])))
                sourcexml.appendChild(configxml)
            
            #Store all sinks
            sinksxml = doc.createElement("datasinks")
            for sink in conduit.datasinks:
                sinkxml = doc.createElement("datasink")
                sinkxml.setAttribute("classname", sink.classname)
                sinksxml.appendChild(sinkxml)
                #Store sink settings
                configurations = sink.module.get_configuration()
                #logging.debug("Sink Settings %s" % configurations)
                for config in configurations:
                    configxml = doc.createElement(str(config))
                    configxml.appendChild(doc.createTextNode(str(configurations[config])))
                    sinkxml.appendChild(configxml)
            conduitxml.appendChild(sinksxml)        

        #FIXME: Save to disk
        print doc.toprettyxml(indent="  ")

    def __main__(self):
        """
        Shows the main window and enters the gtk mainloop
        """
        self.mainWindow.show_all()
        #FIXME: Should I distroy this or is it nicer that it hangs around?
        self.splash.destroy()
        gtk.main()
        
class SplashScreen:
    """
    Simple splash screen class which shows an image for a predetermined period
    of time or until L{SplashScreen.destroy} is called
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
