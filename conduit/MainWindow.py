import gobject
import gtk
import gtk.glade
import gnome.ui

import conduit
import conduit.ConduitEditorCanvas as ConduitEditorCanvas
import conduit.ModuleManager as ModuleManager
import conduit.SyncManager as SyncManager
import conduit.TypeConverter as TypeConverter

class MainWindow:
    """
    The main conduit class.
    """
    
    def __init__(self,name=None):
        gnome.init(conduit.APPNAME, conduit.APPVERSION)
        self.name = name
        self.gladefile = "conduit.glade"
        self.widgets = gtk.glade.XML(self.gladefile, "window1")
        self.widgets.get_widget("window1").set_title(conduit.APPNAME)
    
        #start up the canvas
        self.canvas = ConduitEditorCanvas.ConduitEditorCanvas()
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.canvasSW.add(self.canvas)
        
        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)
        
        dic = { "on_window1_destroy" : self.on_window_closed,
                "on_synchronizebutton_clicked" : self.on_synchronize_clicked,
                "on_configurebutton_clicked" : self.on_configure_clicked,
                "on_linkitemsbutton_clicked" : self.on_link_clicked
                }
         
        self.widgets.signal_autoconnect(dic)

        #Set up the popup widgets
        self.canvas_popup_widgets = gtk.glade.XML(self.gladefile, "menu1")
        self.item_popup_widgets = gtk.glade.XML(self.gladefile, "menu2")        
        self.canvas_popup_widgets.signal_autoconnect(self)
        self.item_popup_widgets.signal_autoconnect(self)        
        
        #Pass both popups to the canvas
        self.canvas.set_popup_menus( 
                                self.canvas_popup_widgets.get_widget("menu1"),
                                self.item_popup_widgets.get_widget("menu2")
                                )
        
        #Dynamically load all datasources, datasinks and datatypes (Python is COOL!)
        self.modules = ModuleManager.ModuleManager(["datatypes","dataproviders"])
        
        #dic = gtk.icon_theme_get_default().list_icons()
        #for d in dic:
        #    print d
                        
        if conduit.DEBUG:
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
        #self.type_converter.print_convertables()


    # callbacks.
    def on_synchronize_clicked(self, widget):
        """
        sync
        """
    	print "clicked synchronize"
    	
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
        print "paste item"
        
    def on_synchronize_item_clicked(self, widget):
        """
        paste item
        """
        print "paste item"    
    

    def on_configure_clicked(self, widget):
        """
        configure
        """
    	print "clicked configure"

    def on_link_clicked(self, widget):
        """
        link
        """
    	print "clicked link"
    	
    def on_window_closed(self, widget):
        """
        Kills the app and cleans up
        """
        gtk.main_quit()

        
    def drop_cb(self, wid, context, x, y, time):
        """
        drop cb
        """
        print "DND DROP = ", context.targets
        self.canvas.drag_get_data(context, context.targets[0], time)
        return True
        
    def drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
        """
        DND
        """
        #print "DND RX = ", context.targets
        #tmodel = treeview.get_model()
        module_name = selection.data
        print "DND DATA ", module_name
        print "X = %s, Y = %s" % (x,y)
        #print "MODEL ", tmodel
        
        #ADD That sausage to the canvas
        m = self.modules.get_module(module_name)
        self.canvas.add_module_to_canvas(m.module, x, y)
        
        context.finish(True, True, etime)
        return        

    def __main__(self):
        gtk.main()    	
