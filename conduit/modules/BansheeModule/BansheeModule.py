import os
import gobject
import logging
log = logging.getLogger("modules.Banshee")

try:
    #python 2.4
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    #python 2.5
    from sqlite3 import dbapi2 as sqlite

import conduit
import conduit.utils as Utils
import conduit.Exceptions as Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Audio as Audio

from gettext import gettext as _

MODULES = {
	"BansheeSource" : { "type": "dataprovider" }
}

ID_IDX = 0
NAME_IDX = 1

class BansheeSource(DataProvider.DataSource):

    _name_ = _("Banshee Playlists")
    _description_ = _("Sync your Banshee playlists")
    _category_ = conduit.dataproviders.CATEGORY_MEDIA
    _module_type_ = "source"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "media-player-banshee"
    _configurable_ = True

    MUSIC_DB = os.path.join(os.path.expanduser("~"),".config", "banshee", "banshee.db")

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #Names of the playlists we know
        self.allPlaylists = []
        #Names we wish to sync
        self.playlists = []
        self.tracks = []


    def _get_all_playlists(self):
        allPlaylists = []
        if os.path.exists(BansheeSource.MUSIC_DB):
            #Create a connection to the database
            con = sqlite.connect(BansheeSource.MUSIC_DB)
            cur = con.cursor()
            #Get a list of all playlists for the config dialog
            cur.execute("SELECT PlaylistID, Name FROM Playlists")
            for playlistid, playlistname in cur:
                allPlaylists.append( (playlistid,playlistname) )
            con.close()

        return allPlaylists

    def initialize(self):
        return True

    def is_configured(self, isSource, isTwoWay):
        return len(self.playlists) > 0
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #only work if Banshee is installed
        if not os.path.exists(BansheeSource.MUSIC_DB):
            raise Exceptions.RefreshError("Banshee is not installed")

        #Stupid pysqlite thread stuff. 
        #Connection must be made in the same thread
        #as any execute statements
        con = sqlite.connect(BansheeSource.MUSIC_DB)
        cur = con.cursor()

        for playlistid in self.playlists:
            cur.execute("select Uri from Tracks INNER JOIN PlaylistEntries ON PlaylistEntries.TrackID=Tracks.TrackID where PlaylistID=%s" % (playlistid))
            for Uri in cur:
                self.tracks.append(Uri[0])

        con.close()

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        return self.tracks

    def get(self, LUID):
        f = Audio.Audio(URI=LUID)
        f.set_UID(LUID)
        f.set_open_URI(LUID)

        return f
    
    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.playlists = []

    def configure(self, window):
        import gtk
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][2] = checked
            val = model[path][ID_IDX]
            if checked and val not in self.playlists:
                self.playlists.append(val)
            elif not checked and val in self.playlists:
                self.playlists.remove(val)

            log.debug("Toggle '%s'(%s) to: %s" % (model[path][NAME_IDX], val, checked))
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"BansheeConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_INT,       #ID_IDX
                                    gobject.TYPE_STRING,    #NAME_IDX
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store
        i = 0
        for t in self._get_all_playlists():
            list_store.append((t[ID_IDX],t[NAME_IDX],t[ID_IDX] in self.playlists))
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

        dlg = tree.get_widget("BansheeConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        dlg.destroy()

    def set_configuration(self, config):
        self.playlists = []
        for playlist in config.get("playlists", []):
            self.playlists.append(playlist)
            
    def get_configuration(self):
        return { "playlists" : self.playlists }

    def get_UID(self):
        return Utils.get_user_string()


