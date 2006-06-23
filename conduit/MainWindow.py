import pygtk
pygtk.require("2.0")

import gst
import gobject
import gtk
import gtk.glade
import gnome.ui

import DataProvider
import ConduitEditorCanvas
import Manager


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
        
        #populate the treeview
        self.listmodel = Manager.DataProviderTreeModel()
        self.treeview = self.widgets.get_widget("treeview1")
        # create the TreeViewColumns to display the data
        column_names = self.listmodel.get_column_names()
        self.tvcolumn = [None] * len(column_names)
        cellpb = gtk.CellRendererPixbuf()
        self.tvcolumn[0] = gtk.TreeViewColumn(column_names[0],
                                              cellpb, pixbuf=0)
        cell = gtk.CellRendererText()
        self.tvcolumn[0].pack_start(cell, False)
        self.tvcolumn[0].add_attribute(cell, 'text', 1)
        self.treeview.append_column(self.tvcolumn[0])
        for n in range(1, len(column_names)):
            cell = gtk.CellRendererText()
            if n == 1:
                cell.set_property('xalign', 1.0)
            self.tvcolumn[n] = gtk.TreeViewColumn(column_names[n], cell, text=n+1)
            self.treeview.append_column(self.tvcolumn[n])
            
        self.treeview.set_model(self.listmodel)
        #self.widgets.show_all()            
    
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
        
        self.m = Manager.ModuleLoader(["datatypes","dataproviders"])
        self.m.load_all()
        #for q in self.m.loadedmodules:
        #    print "Name = '%s' Description = '%s' Type = '%s'" % (q.name, q.description, q.module_type)
        #    print "Raw ", q.module
        return
     
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
