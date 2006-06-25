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
        self.source_scrolled_window.add(self.modules.get_treeview("source"))
        self.sink_scrolled_window.add(self.modules.get_treeview("sink"))
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
        
    def drop_cb(self, wid, context, x, y, time):
        print "DND DROP = ", context.targets
        self.canvas.drag_get_data(context, context.targets[0], time)
        #text.join([str(t) for t in context.targets])
        #print text
        return True
        
    def drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
        print "DND RX = ", context.targets
        tmodel = treeview.get_model()
        tdata = selection.data
        print "TREEVIEW ", treeview
        print "CONTEXT ", context
        print "SELECTION ", selection
        print "INFO ", info
        print "DATA ", tdata
        print "MODEL ", tmodel
        #drop_info = treeview.get_dest_row_at_pos(x, y)
        #if drop_info:
        #    path, position = drop_info
        #    iter = model.get_iter(path)
        #    if (position == gtk.TREE_VIEW_DROP_BEFORE
        #        or position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
        #        model.insert_before(iter, [data])
        #    else:
        #        model.insert_after(iter, [data])
        #else:
        #    model.append([data])
        #if context.action == gtk.gdk.ACTION_MOVE:
        #mod_wrapper = tmodel.get_module_by_name(tdata)
        context.finish(True, True, etime)
        return        

    def __main__(self):
        gtk.main()    	
