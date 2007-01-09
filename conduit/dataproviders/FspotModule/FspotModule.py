import gtk
import gobject
from gettext import gettext as _
from pysqlite2 import dbapi2 as sqlite

import logging
import conduit
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File

import os
import os.path


MODULES = {
	"FspotSource" : { "type": "dataprovider" }
}

ID_IDX = 0
NAME_IDX = 1

class FspotSource(DataProvider.DataSource):

    _name_ = _("F-Spot Photos")
    _description_ = _("Sync your F-Spot photos")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "taggedfile"
    _out_type_ = "taggedfile"
    _icon_ = "f-spot"

    PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #Settings
        self.enabledTags = []
        self.photoURIs = None

        self.tags = []
        self._get_all_tags()

    def _get_all_tags(self):
        self.tags = []
        if os.path.exists(FspotSource.PHOTO_DB):
            #Create a connection to the database
            con = sqlite.connect(FspotSource.PHOTO_DB)
            cur = con.cursor()
            #Get a list of all tags for the config dialog
            cur.execute("SELECT id, name FROM tags")
            for (tagid, tagname) in cur:
                self.tags.append([tagid,tagname])
            con.close()  

    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self._get_all_tags()
        #Stupid pysqlite thread stuff. Connection must be made in the same thread
        #as any execute statements
        self.photoURIs = []
        #Create a connection to the database
        con = sqlite.connect(FspotSource.PHOTO_DB)
        tagCur = con.cursor()
        photoCur = con.cursor()
        for tag in self.enabledTags:
            tagCur.execute("SELECT photo_id FROM photo_tags WHERE tag_id=%s" % (tag[ID_IDX]))
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
        return {"enabledTags" : self.enabledTags}

    def configure(self, window):
        """
        Indeed
        """
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][2] = checked
            val = model[path][ID_IDX]
            if checked and val not in self.enabledTags:
                self.enabledTags.append(val)
            elif not checked and val in self.enabledTags:
                self.enabledTags.remove(val)

            logging.debug("Toggle '%s'(%s) to: %s" % (model[path][NAME_IDX], val, checked))
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FspotConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_STRING,    #ID_IDX
                                    gobject.TYPE_STRING,    #NAME_IDX
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store
        self._get_all_tags()
        i = 0
        for t in self.tags:
            list_store.append((t[ID_IDX],t[NAME_IDX],t[ID_IDX] in self.enabledTags))
            i += 1
        #Set up the treeview
        tagtreeview.set_model(list_store)
        #column 1 is the tag name
        tagtreeview.append_column(  gtk.TreeViewColumn('Tag Name', 
                                    gtk.CellRendererText(), 
                                    text=NAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn('Enabled', 
                                    renderer1, 
                                    active=2)
                                    )

        dlg = tree.get_widget("FspotConfigDialog")
        dlg.set_transient_for(window)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            #print self.tags
            pass
        dlg.destroy()

    def get_UID(self):
        return ""


