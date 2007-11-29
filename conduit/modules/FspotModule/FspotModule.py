import os
import gobject
import logging
log = logging.getLogger("modules.Fspot")

try:
    #python 2.4
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    #python 2.5
    from sqlite3 import dbapi2 as sqlite

import conduit
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Photo as Photo

from gettext import gettext as _

MODULES = {
	"FspotSource" : { "type": "dataprovider" }
}

ID_IDX = 0
NAME_IDX = 1

PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")

# check if path exists
if not os.path.exists(PHOTO_DB):
    raise Exceptions.NotSupportedError("No F-Spot database found")

class FspotSource(DataProvider.DataSource):

    _name_ = _("F-Spot Photos")
    _description_ = _("Sync your F-Spot photos")
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _module_type_ = "source"
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"
    _icon_ = "f-spot"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)

        self.need_configuration(True)
        #Settings
        self.enabledTags = []
        self.photos = []

    def _get_all_tags(self):
        tags = []
        if os.path.exists(PHOTO_DB):
            #Create a connection to the database
            con = sqlite.connect(PHOTO_DB)
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
        if not os.path.exists(PHOTO_DB):
            raise Exceptions.RefreshError("Fspot is not installed")

        #Stupid pysqlite thread stuff. 
        #Connection must be made in the same thread
        #as any execute statements
        con = sqlite.connect(PHOTO_DB)
        cur = con.cursor()

        for tagID in self.enabledTags:
            cur.execute("SELECT photo_id FROM photo_tags WHERE tag_id=%s" % (tagID))
            for photo_uid in cur:
                self.photos.append(photo_uid[0])

        con.close()

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        return self.photos

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)

        con = sqlite.connect(PHOTO_DB)
        cur = con.cursor()
        cur.execute("SELECT directory_path, name FROM photos WHERE id=?", (LUID, ))
        directory_path, name = cur.fetchone()        
        con.close()

        photouri = directory_path + "/" + name

        f = Photo.Photo(URI=photouri)
        f.set_UID(LUID)
        f.set_open_URI(photouri)

        return f
    
    def finish(self):
        DataProvider.DataSource.finish(self)
        self.photos = []

    def configure(self, window):
        import gtk
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][2] = checked
            val = model[path][ID_IDX]
            if checked and val not in self.enabledTags:
                self.enabledTags.append(val)
            elif not checked and val in self.enabledTags:
                self.enabledTags.remove(val)

            log.debug("Toggle '%s'(%s) to: %s" % (model[path][NAME_IDX], val, checked))
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
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Tag Name"), 
                                    gtk.CellRendererText(), 
                                    text=NAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Enabled"), 
                                    renderer1, 
                                    active=2)
                                    )

        dlg = tree.get_widget("FspotConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.set_configured(True)
        dlg.destroy()

    def set_configuration(self, config):
        self.enabledTags = []
        for tag in config.get("tags", []):
            self.enabledTags.append(int(tag))

        self.set_configured(True)
            
    def get_configuration(self):
        strTags = []
        for tag in self.enabledTags:
            strTags.append(str(tag))
        return {"tags": strTags}

    def get_UID(self):
        return Utils.get_user_string()


