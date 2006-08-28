import gtk
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
		"category": "Photos",
		"in_type": "file",
		"out_type": "file"
	}
}

class FspotSource(DataProvider.DataSource):
    PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Fspot Photos"), _("Source for Fspot Photos"))
        #self.icon_name = "tomboy"
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
                self.tags.append({"Id" : tagid, "Name" : tagname})
            
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
