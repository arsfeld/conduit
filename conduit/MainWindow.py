import sys
import gtk
import gtk.glade
import diacanvas

import ConduitDefs
import DataProvider
from datasources import FileSource
import datasinks

class MainWindow:
    def __init__(self):
        self.gladefile = ConduitDefs.GLADE_FILE
        self.mainwindowname = "window1"
        self.wTree = gtk.glade.XML(self.gladefile, self.mainwindowname)
        self.win = self.wTree.get_widget(self.mainwindowname)
        self.win.maximize()
        dic = {"on_window1_destroy" : gtk.main_quit,
            "on_synchronizebutton_clicked" : self.synchronizeSet,
            "on_configurebutton_clicked" : self.configureItem,
            "on_linkitemsbutton_clicked" : self.linkItem
            }
         
        self.wTree.signal_autoconnect(dic)
    
        #insert the canvas
        self.canvas = diacanvas.Canvas()
        self.box = FileSource.FileSource() 
        #box = diacanvas.CanvasBox()
        #box.set(border_width=0.3, color=diacanvas.color(150, 150, 150, 128))
        self.canvas.root.add(self.box)
        self.box.move(100,100)

        self.canvasW = self.wTree.get_widget("canvasScrolledWindow")
        view = diacanvas.CanvasView(canvas = self.canvas)
        view.show()
        self.canvasW.add(view)
        return
     
    # callbacks.
    def synchronizeSet(self, widget):
    	print "clicked synchronize"
    

    def configureItem(self, widget):
    	print "clicked configure"


    def linkItem(self, widget):
    	print "clicked link"
