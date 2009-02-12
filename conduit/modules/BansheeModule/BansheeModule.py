# Banshee-1 support added by Andrew Stormont <andyjstormont@googlemail.com>
# I've tried to keep compatability for Banshee < 1, it should work fine.
# Saved playlists should also be remebered, this all needs testing though.

# FIXME: This doesn't handle folders and never did, should it?

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

BANSHEE_INSTALLED = False
BANSHEE_VERSION_1 = False
BANSHEE_BASE_LOCATION = ""

if Utils.program_installed("banshee"):
    BANSHEE_INSTALLED = True
elif Utils.program_installed("banshee-1"):
    BANSHEE_INSTALLED = True
    BANSHEE_VERSION_1 = True
    import gconf
    BANSHEE_BASE_LOCATION = "file://%s/" % gconf.Client().get_string( "/apps/banshee-1/library/base_location" )

if BANSHEE_INSTALLED:
    MODULES = {
    	"BansheeSource" : { "type": "dataprovider" }
    }
else:
    MODULES = {}

(ID_IDX, NAME_IDX, CHECKED_IDX, TYPE_IDX) = range( 4 )
(SMART_PLAYLIST, NORMAL_PLAYLIST, VIDEO_PLAYLIST) = range( 1, 4 ) # FIXME should these be hard coded?

class BansheeSource(DataProvider.DataSource):

    _name_ = _("Banshee Playlists")
    _description_ = _("Synchronize your Banshee playlists")
    _category_ = conduit.dataproviders.CATEGORY_MEDIA
    _module_type_ = "source"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "media-player-banshee"
    _configurable_ = True

    if BANSHEE_VERSION_1:
        MUSIC_DB = os.path.join(os.path.expanduser("~"),".config", "banshee-1", "banshee.db")
    else:
        MUSIC_DB = os.path.join(os.path.expanduser("~"),".config", "banshee", "banshee.db")

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #Names of the playlists we know
        self.allPlaylists = []
        self.update_configuration(
            #Playlist Ids we wish to sync
            playlists = [],
            smart_playlists = [],
            video_playlists = [],
        }
        self.tracks = []

    def _get_full_uri(self, uri):
        if not uri.startswith("file://"):
            return BANSHEE_BASE_LOCATION + uri

    def _get_all_playlists(self):
        allPlaylists = []
        if os.path.exists(BansheeSource.MUSIC_DB):
            #Create a connection to the database
            con = sqlite.connect(BansheeSource.MUSIC_DB)
            cur = con.cursor()
            #Get a list of all playlists for the config dialog
            #If we don't convert all the id's to strings Settings.py will spazz
            if BANSHEE_VERSION_1:
                cur.execute("SELECT PlaylistID, Name FROM CorePlaylists where PrimarySourceID NOT NULL") # NULL = "Play Queue"
                for playlistid, playlistname in cur:
                    allPlaylists.append( {
                        "id"   : str( playlistid ),
                        "name" : playlistname,
                        "type" : NORMAL_PLAYLIST
                    } )
                cur.execute("SELECT SmartPlaylistID, Name FROM CoreSmartPlaylists where PrimarySourceID=%s" % SMART_PLAYLIST)
                for playlistid, playlistname in cur:
                    allPlaylists.append( {
                        "id"   : str( playlistid ),
                        "name" : playlistname,
                        "type" : SMART_PLAYLIST
                    } )
                cur.execute("SELECT SmartPlaylistID, Name FROM CoreSmartPlaylists where PrimarySourceID=%s" % VIDEO_PLAYLIST)
                for playlistid, playlistname in cur:
                    allPlaylists.append( {
                        "id"   : str( playlistid ),
                        "name" : playlistname,
                        "type" : VIDEO_PLAYLIST
                    } )
            else:
                cur.execute("SELECT PlaylistID, Name FROM Playlists")
                for playlistid, playlistname in cur:
                    allPlaylists.append( { 
                        "id"   : str( playlistid ), 
                        "name" : playlistname,
                        "type" : NORMAL_PLAYLIST 
                    } )
            con.close()
        return allPlaylists

    def initialize(self):
        return True

    def is_configured(self, isSource, isTwoWay):
        return len(self.playlists+self.smart_playlists+self.video_playlists) > 0
        
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
            if BANSHEE_VERSION_1:
                cur.execute("select Uri from CoreTracks INNER JOIN CorePlaylistEntries ON CorePlaylistEntries.TrackID=CoreTracks.TrackID where PlaylistID=%s" % (playlistid))
            else:
                cur.execute("select Uri from Tracks INNER JOIN PlaylistEntries ON PlaylistEntries.TrackID=Tracks.TrackID where PlaylistID=%s" % (playlistid))
            for Uri in cur:
                self.tracks.append( self._get_full_uri( Uri[0] ) )

        for playlistid in self.smart_playlists + self.video_playlists:
            cur.execute("select Uri from CoreTracks INNER JOIN CoreSmartPlaylistEntries ON CoreSmartPlaylistEntries.TrackID where PlaylistID=%s" % (playlistid))
            for Uri in cur:
                self.tracks.append( self._get_full_uri( Uri[0] ) )
        con.close()

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        return self.tracks

    def get(self, LUID):
        f = Audio.Audio(URI=LUID)
        f.set_UID(LUID)
        f.set_open_URI(LUID)
        return f

    def config_setup(self, config):
        config.add_section("Playlists")
        config.add_item("Playlists", "list", 
            config_name = "playlists",
            choices = self._get_all_playlists()
        )
    
    '''
    def configure_(self, window):
        import gtk
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][CHECKED_IDX] = checked
            ( Name, Id, Type ) = ( model[path][NAME_IDX], model[path][ID_IDX], model[path][TYPE_IDX] )
            if Type == NORMAL_PLAYLIST:
                if checked and Name not in self.playlists:
                    self.playlists.append(Id)
                elif not checked and Name in self.playlists:
                    self.playlists.remove(Id)
            elif Type == SMART_PLAYLIST:
                if checked and Name not in self.smart_playlists:
                    self.smart_playlists.append(Id)
                elif not checked and Name in self.smart_playlists:
                    self.smart_playlists.remove(Id)
            elif Type == VIDEO_PLAYLIST:
                if checked and Name not in self.video_playlists:
                    self.video_playlists.append(Id)
                elif not checked and Name in self.video_playlists:
                    self.video_playlists.remove(Id)
            log.debug("Toggle name: '%s', type: '%s', id: '%s' to: %s" % (Name, Type, Id, checked))
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "BansheeConfigDialog"
        )
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_STRING,    #ID_IDX      - 0
                                    gobject.TYPE_STRING,    #NAME_IDX    - 1
                                    gobject.TYPE_BOOLEAN,   #CHECKED_IDX - 2
                                    gobject.TYPE_INT,       #TYPE_IDX    - 3
                                    )
        #Fill the list store
        for playlist in self._get_all_playlists():
            if playlist["type"] == NORMAL_PLAYLIST and playlist["id"] in self.playlists:
                checked = True
            elif playlist["type"] == SMART_PLAYLIST and playlist["id"] in self.smart_playlists:
                checked = True
            elif playlist["type"] == VIDEO_PLAYLIST and playlist["id"] in self.video_playlists:
                checked = True
            else:
                checked = False
            # Make video playlists more obvious
            if playlist["type"] == VIDEO_PLAYLIST:
                playlist["name"] += " (Video)"
            list_store.append( ( playlist["id"], playlist["name"], checked, playlist["type"] ) )
                     
        #Set up the treeview
        tagtreeview.set_model(list_store)
        #column 1 is the tag name
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Playlist Name"), # Tag name is confusing?
                                    gtk.CellRendererText(), 
                                    text=NAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Enabled"), 
                                    renderer1, 
                                    active=CHECKED_IDX)
                                    )

        dlg = tree.get_widget("BansheeConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        dlg.destroy()

    def get_UID(self):
        return Utils.get_user_string()


