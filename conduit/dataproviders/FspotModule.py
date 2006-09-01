import gtk
import gobject
from gettext import gettext as _
from pysqlite2 import dbapi2 as sqlite

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File

import os
import os.path


MODULES = {
	"FspotSource" : {
		"name": _("Fspot Photos"),
		"description": _("Source for Fspot Photos"),
		"type": "source",
		"category": DataProvider.CATEGORY_LOCAL,
		"in_type": "file",
		"out_type": "file"
	}
}

class FspotSource(DataProvider.DataSource):
    PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Fspot Photos"), _("Source for Fspot Photos"))
        self.icon_name = "f-spot"
        #DB stuff
        self.con = None
        self.cur = None
        #Settings
        self.tags = []
        self.photoURIs = []

    def initialize(self):
        if not os.path.exists(FspotSource.PHOTO_DB):
            return False
        else:
            #Create a connection to the database
            self.con = sqlite.connect(FspotSource.PHOTO_DB)
            self.cur = self.con.cursor()

            #Get a list of all tags for the config dialog
            self.cur.execute("SELECT id, name FROM tags")
            for (tagid, tagname) in self.cur:
                self.tags.append([{"Id" : tagid, "Name" : tagname}, False])
            
            self.con.close()  
            return True
        
    def refresh(self):
        #Stupid pysqlite thread stuff. Connection must be made in the same thread
        #as any execute statements

        #Create a connection to the database
        self.con = sqlite.connect(FspotSource.PHOTO_DB)
        self.cur = self.con.cursor()
        #FIXME: Should only get ones associated with the selected tag
        self.cur.execute("SELECT directory_path, name FROM photos")
        for (directory_path, name) in self.cur:
            self.photoURIs.append(os.path.join(directory_path, name))
        self.con.close()

    def get(self):
        for uri in self.photoURIs:
            f = File.File()
            f.load_from_uri(str(uri))
            yield f

    def configure(self, window):
        """
        Indeed
        """
        def col1_toggled_cb(cell, path, model ):
            model[path][1] = not model[path][1]
            logging.debug("Toggle '%s' to: %s (%s)" % (model[path][0], model[path][1], model[path][2]))
            #This is why we stored the tag index...
            self.tags[ model[path][2] ][1] = model[path][1]
            return

        tree = gtk.glade.XML(conduit.GLADE_FILE, "FspotConfigDialog")
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_STRING,
                                    gobject.TYPE_BOOLEAN,
                                    gobject.TYPE_INT #Also store the tag index
                                    )
        #Fill the list store
        i = 0
        for t in self.tags:
            list_store.append((t[0]["Name"],t[1],i))
            i += 1
        #Set up the treeview
        tagtreeview.set_model(list_store)
        #column 1 is the tag name
        tagtreeview.append_column(  gtk.TreeViewColumn('Tag Name', 
                                    gtk.CellRendererText(), 
                                    text=0)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn('Enabled', 
                                    renderer1, 
                                    active=1)
                                    )

        dlg = tree.get_widget("FspotConfigDialog")
        dlg.set_transient_for(window)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            print self.tags
        dlg.destroy()

