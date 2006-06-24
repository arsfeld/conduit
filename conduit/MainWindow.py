import pygtk
pygtk.require("2.0")

import gst
import gobject
import gtk
import gtk.glade
import gnome.ui

import DataProvider
import ConduitEditorCanvas
import ModuleManager


APPNAME="Conduit"
APPVERSION="0.0.1"

class MainWindow:
    def __init__(self,name=None):
        gnome.init(APPNAME, APPVERSION)
        self.name = name
        self.gladefile = "conduit.glade"
        self.widgets = gtk.glade.XML(self.gladefile, "window1")
    
        #start up the canvas
        self.canvas = ConduitEditorCanvas.ConduitEditorCanvas()
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.canvasSW.add(self.canvas)
        
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
        self.module_loader = ModuleManager.ModuleLoader(["datatypes","dataproviders"])
        self.module_loader.load_all_modules()
        #Split into sinks, sources and datatypes
        self.datasink_modules = self.module_loader.get_modules("sink")
        self.datasource_modules = self.module_loader.get_modules("source")
        self.datatypes = self.module_loader.get_modules("datatype")
        
        if False:
            print "SINKS"
            for q in self.datasink_modules:
                print "Name = '%s' Description = '%s' Type = '%s' Category = '%s'" % (q.name, q.description, q.module_type, q.category)
                print "Raw ", q.module
            
            print "SOURCES"
            for q in self.datasource_modules:
                print "Name = '%s' Description = '%s' Type = '%s' Category = '%s'" % (q.name, q.description, q.module_type, q.category)
                print "Raw ", q.module
            
            print "TYPES"
            for q in self.datatypes:
                print "Name = '%s' Description = '%s' Type = '%s' Category = '%s'" % (q.name, q.description, q.module_type, q.category)
                print "Raw ", q.module
                
        
        # Populate the tree and list models
        self.source_scrolled_window = self.widgets.get_widget("scrolledwindow2")
        self.sink_scrolled_window = self.widgets.get_widget("scrolledwindow3")
        self.source_model = ModuleManager.DataProviderTreeModel(self.datasource_modules)            
        self.sink_model = ModuleManager.DataProviderTreeModel(self.datasink_modules)
        self.source_tree_view = ModuleManager.DataProviderTreeView(self.source_model)
        self.sink_tree_view = ModuleManager.DataProviderTreeView(self.sink_model)
        self.source_scrolled_window.add(self.source_tree_view)
        self.sink_scrolled_window.add(self.sink_tree_view)
        self.source_scrolled_window.show_all()
        self.sink_scrolled_window.show_all()

        #self.widgets.show_all()
     
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

        #diawidget = gtk.glade.XML(self.gladefile, "addElementDialog")
        #dialog = diawidget.get_widget("addElementDialog")

        #build a list of all usable gst elements
        #registry = gst.registry_get_default()
        #registrylist = registry.get_feature_list(gst.ElementFactory)    

        #populate the tree
        #treemodel = gtk.TreeStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING)
        #for item in registrylist:
        #    treemodel.append(None, [item, item.get_name()])

        #display view
        #treeview = diawidget.get_widget("elementListView")
        #treeview.set_model(treemodel)
        #renderer = gtk.CellRendererText()
        #column = gtk.TreeViewColumn("Element", renderer, text=1)
        #treeview.append_column(column)
        #treeview.show()

        #rtn = dialog.run()
        #if (rtn != gtk.RESPONSE_OK):
        #    print "no element selected"
        #else:
            #find out which element was selected
        #    selected = treeview.get_selection()
        #    model, select = selected.get_selected()
        #    newfactory = model.get_value(select, 0)
            #give it to the canvas to instantiate and draw
        #    self.canvas.makeNewElement(None, newfactory)
        #clean up
        #dialog.destroy()
        return

    def setPlayMode(self, mode):
        "Set the pipeline to be playing, paused, etc."
        raise NotImplementedError

    def testPrint(self, button):
        print "hello!"
        return 1

    def __main__(self):
        gtk.main()    	
