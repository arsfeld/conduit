import gobject
import gtk
import gtk.glade
import gnome.ui

import conduit
import conduit.ConduitEditorCanvas as ConduitEditorCanvas
import conduit.ModuleManager as ModuleManager
import conduit.SyncManager as SyncManager

class MainWindow:
    """
    The main conduit class.
    """
    
    def __init__(self,name=None):
        gnome.init(conduit.APPNAME, conduit.APPVERSION)
        self.name = name
        self.gladefile = "conduit.glade"
        self.widgets = gtk.glade.XML(self.gladefile, "window1")
    
        #start up the canvas
        self.canvas = ConduitEditorCanvas.ConduitEditorCanvas()
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.canvasSW.add(self.canvas)
        
        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)
        
        dic = {"on_window1_destroy" : gtk.main_quit,
            "on_synchronizebutton_clicked" : self.synchronizeSet,
            "on_configurebutton_clicked" : self.configureItem,
            "on_linkitemsbutton_clicked" : self.linkItem
            }
         
        self.widgets.signal_autoconnect(dic)

        #pass the popup menu to the canvas
        self.popwidgets = gtk.glade.XML(self.gladefile, "menu1")
        popup = self.popwidgets.get_widget("menu1")
        self.popwidgets.signal_autoconnect(self)
        self.canvas.setPopup(popup)
        
        #Dynamically load all datasources, datasinks and datatypes (Python is COOL!)
        self.modules = ModuleManager.ModuleManager(["datatypes","dataproviders"])
                
        if True:
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

    # callbacks.
    def synchronizeSet(self, widget):
    	print "clicked synchronize"
    

    def configureItem(self, widget):
    	print "clicked configure"

    def linkItem(self, widget):
    	print "clicked link"
    	
    def _loadFromFile(self, widget, event):
        "Load GST Editor pipeline setup from a file and initialize" 
        raise NotImplementedError

    def _destroyWindow(self, widget):
        "Kills the app and cleans up"
        gtk.main_quit()

    def _addElementPopup(self, event):
        "Calls add element from a popup menu selection"
        self._addElement(None, event)

    def _addElement(self, widget, event):
        "Pops open a dialog and adds a GST element to the editor pipeline"
        print "cheese"
        return

    def setPlayMode(self, mode):
        "Set the pipeline to be playing, paused, etc."
        raise NotImplementedError

    def drop_cb(self, wid, context, x, y, time):
        print "DND DROP = ", context.targets
        self.canvas.drag_get_data(context, context.targets[0], time)
        return True
        
    def drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
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
