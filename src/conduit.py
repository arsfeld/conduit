try:
    import pygtk
    pygtk.require("2.0")
except:
    pass
try:
    import gtk
    import gtk.glade
except:
    sys.exit(1)
 
class conduitGui:
    def __init__(self):
        self.gladefile = "conduit.glade"
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
	return
     
    # callbacks.
    def synchronizeSet(self, widget):
	print "clicked synchronize"
    

    def configureItem(self, widget):
	print "clicked configure"


    def linkItem(self, widget):
	print "clicked link"


app = conduitGui()
gtk.main()
     
 
