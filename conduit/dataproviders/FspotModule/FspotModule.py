import os
import gtk
import gobject
from pysqlite2 import dbapi2 as sqlite

import conduit
from conduit import logd
import conduit.Utils as Utils
import conduit.Exceptions
import conduit.DataProvider as DataProvider
import conduit.datatypes.File as File

MODULES = {
	"FspotSource" : { "type": "dataprovider" }
}

ID_IDX = 0
NAME_IDX = 1

class FspotSource(DataProvider.DataSource):

    _name_ = "F-Spot Photos"
    _description_ = "Sync your F-Spot photos"
    _category_ = DataProvider.CATEGORY_PHOTOS
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "f-spot"

    PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.need_configuration(True)
        #Settings
        self.enabledTags = []
        self.photos = []

    def _get_all_tags(self):
        tags = []
        if os.path.exists(FspotSource.PHOTO_DB):
            #Create a connection to the database
            con = sqlite.connect(FspotSource.PHOTO_DB)
            cur = con.cursor()
            #Get a list of all tags for the config dialog
            cur.execute("SELECT id, name FROM tags")
            for tagid, tagname in cur:
                tags.append( (tagid,tagname) )
            con.close()

        return tags

    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #only work if Fspot is installed
        if not os.path.exists(FspotSource.PHOTO_DB):
            raise Exceptions.RefreshError("Fspot is not installed")

        #Stupid pysqlite thread stuff. 
        #Connection must be made in the same thread
        #as any execute statements
        con = sqlite.connect(FspotSource.PHOTO_DB)
        tagCur = con.cursor()
        photoCur = con.cursor()
        for tagID in self.enabledTags:
            tagCur.execute("SELECT photo_id FROM photo_tags WHERE tag_id=%s" % (tagID))
            for photoID in tagCur:
                photoCur.execute("SELECT directory_path, name FROM photos WHERE id=?", (photoID))
                for directory_path, name in photoCur:
                    #Return the file, loaded from a (local only??) URI
                    if type(photoID) == tuple:
                        uid = photoID[0]
                    else:
                        logw("Error getting photo ID")
                        uid = photoID

                    logd("Found photo with name=%s (ID: %s)" % (name,uid))
                    self.photos.append( (os.path.join(directory_path, name),uid) )

        con.close()
        
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        photouri, photouid = self.photos[index]

        f = File.File(URI=photouri)
        f.set_UID(photouid)
        f.set_open_URI(photouri)

        return f

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.photos)
    
    def finish(self):
        DataProvider.DataSource.finish(self)
        self.photos = []

    def configure(self, window):
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][2] = checked
            val = model[path][ID_IDX]
            if checked and val not in self.enabledTags:
                self.enabledTags.append(val)
            elif not checked and val in self.enabledTags:
                self.enabledTags.remove(val)

            logd("Toggle '%s'(%s) to: %s" % (model[path][NAME_IDX], val, checked))
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FspotConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_INT,       #ID_IDX
                                    gobject.TYPE_STRING,    #NAME_IDX
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store
        i = 0
        for t in self._get_all_tags():
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
            self.set_configured(True)
        dlg.destroy()

    def get_UID(self):
        return Utils.get_user_string()


