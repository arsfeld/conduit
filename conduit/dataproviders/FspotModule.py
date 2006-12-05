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
		"in_type": "taggedfile",
		"out_type": "taggedfile",
                "icon": "f-spot"
	}
}

class FspotSource(DataProvider.DataSource):
    PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Fspot Photos"), _("Source for Fspot Photos"), "f-spot")
        #Settings
        self.enabledTags = [] #Just used to save and restore settings
        self.tags = []
        self.photoURIs = None

    def initialize(self):
        if not os.path.exists(FspotSource.PHOTO_DB):
            return False
        else:
            #Create a connection to the database
            con = sqlite.connect(FspotSource.PHOTO_DB)
            cur = con.cursor()

            #Get a list of all tags for the config dialog
            cur.execute("SELECT id, name FROM tags")
            for (tagid, tagname) in cur:
                self.tags.append([{"Id" : tagid, "Name" : tagname}, False])
            
            con.close()  
            return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)

        #Stupid pysqlite thread stuff. Connection must be made in the same thread
        #as any execute statements
        self.photoURIs = []
        #Create a connection to the database
        con = sqlite.connect(FspotSource.PHOTO_DB)
        tagCur = con.cursor()
        photoCur = con.cursor()
        for tag in [t for t in self.tags if t[1]]:
            tagCur.execute("SELECT photo_id FROM photo_tags WHERE tag_id=%s" % (tag[0]["Id"]))
            for photoID in tagCur:
                photoCur.execute("SELECT directory_path, name FROM photos WHERE id=?", (photoID))
                for (directory_path, name) in photoCur:
                    #Return the file, loaded from a (local only??) URI
                    logging.debug("Found photo with name=%s" % name)
                    self.photoURIs.append(os.path.join(directory_path, name))

        con.close()
        
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return self.photoURIs[index]

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.photoURIs)
    
    def finish(self):
        self.photoURIs = None

    def set_configuration(self, config):
        #We need to override set_configuration because we need to fold the
        #list of enabled tags into the datastore that is used for the
        #config dialog
        if not config.has_key("enabledTags"):
            return
        #This is a bit of a hack (i.e. inefficient - looped in statement) way 
        #to set the default enabled tags
        for t in self.tags:
            if t[0]["Name"] in config["enabledTags"]:
                logging.debug("Renabling %s tag" % t[0]["Name"])
                t[1] = True
            

    def get_configuration(self):
        #Save enabled tags
        return {"enabledTags" : [ t[0]["Name"] for t in self.tags if t[1] ]}        

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
            #print self.tags
            pass
        dlg.destroy()

