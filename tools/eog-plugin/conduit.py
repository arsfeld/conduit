import os

import eog
import gtk, gtk.glade

#if this code is a bit convoluted and jumps around a lot
#it is because I lazy initialize everything to minimise 
#the work that occurs at startup time

class ConduitPlugin(eog.Plugin):
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(__file__, ".."))
        self.gladefile = os.path.join(self.dir, "config.glade")
        self.store = gtk.TreeStore(gtk.gdk.Pixbuf,str)
        
        self.dlg = None

    def _dummy_data(self):
        img = gtk.gdk.pixbuf_new_from_file(os.path.join(self.dir, "conduit-icon.png"))
        self.store.append(None,(img, "Text"))

    def _prepare_sidebar(self, window):
        #the sidebar is a treeview where 
        #photos to upload are grouped by the
        #upload service, with a clear button and
        #a upload button below

        box = gtk.VBox()
        view = gtk.TreeView(self.store)
        box.pack_start(view,expand=True,fill=True)
        bbox = gtk.HButtonBox()
        box.pack_start(bbox,expand=False)
        
        #two colums, a icon and a description/name
        col0 = gtk.TreeViewColumn("Pic", gtk.CellRendererPixbuf(), pixbuf=0)
        col1 = gtk.TreeViewColumn("Name", gtk.CellRendererText(), text=1)
        view.append_column(col0)
        view.append_column(col1)
        view.set_headers_visible(False)

        #upload and clear button
        okbtn = gtk.Button(stock=gtk.STOCK_OK)
        clearbtn = gtk.Button(stock=gtk.STOCK_CLEAR)
        bbox.pack_start(okbtn)
        bbox.pack_start(clearbtn)

        sidebar = window.get_sidebar()
        sidebar.add_page("Conduit", box)
        sidebar.show_all()

    def _prepare_config_dialog(self):
        if self.dlg == None:
            xml = gtk.glade.XML(self.gladefile, "ConfigDialog")
            self.dlg = xml.get_widget("ConfigDialog")

    def activate(self, window):
        self._prepare_sidebar(window) 
        self._dummy_data()       
        print "ACTIVATE"

    def deactivate(self, window):
        print "DEACTIVATE"

    def update_ui(self, window):
        print "UPDATE"

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        self._prepare_config_dialog()
        return self.dlg
