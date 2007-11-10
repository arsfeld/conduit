"""
Provides a simple means for reading rhythmbox static playlists.

Based upon code from 

Copyright 2007: John Stowers
License: GPLv2
"""
import urllib
import os
import logging
log = logging.getLogger("modules.Rhythmbox")


try:
    import elementtree.ElementTree as ET
except:
    import xml.etree.ElementTree as ET

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.datatypes.Audio as Audio

MODULES = {
    "RhythmboxSource" :              { "type": "dataprovider" },
}

#list store column define
NAME_IDX=0
CHECK_IDX=1

class RhythmboxSource(DataProvider.DataSource):

    _name_ = "Rhythmbox Music"
    _description_ = "Sync songs from your Rhythmbox playlists"
    _category_ = conduit.dataproviders.CATEGORY_MEDIA
    _module_type_ = "source"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "rhythmbox"

    PLAYLIST_PATH="~/.gnome2/rhythmbox/playlists.xml"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #Names of the playlists we know
        self.allPlaylists = []
        #Names we wish to sync
        self.playlists = []

    def _parse_playlists(self, path, allowed=[]):
        playlists = []
        songs = []
        playlist_name = u"Unknown"
        is_static = False

        path = os.path.expanduser(path) 
        
        root = ET.ElementTree(file=path)
        iter = root.getiterator()
        for element in iter:

            if element.tag == "playlist":
                is_static = False

                if element.keys():
                    for name, value in element.items():
                        if name == "type" and value == "static":
                            is_static = True
                        if name == "name":
                            temp_name = value

                if is_static == True: # new playlist found
                    playlist_name = temp_name
                    songs = []
                    playlists.append( [playlist_name, songs] )

            #Text that precedes all child elements (may be None)
            if element.text:
                text = element.text
            if element.tag == "location":
                song_location = ''.join(urllib.url2pathname(text).split("://")[1:])

                if not os.path.exists(song_location):
                    print "WARNING: A song referred to from the playlist '%s' cannot be found on the harddrive." % playlist_name
                    continue

                songs.append( song_location )

        return playlists

    def configure(self, window):
        import gtk
        import gobject
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][CHECK_IDX] = checked
            val = model[path][NAME_IDX]
            if checked and val not in self.playlists:
                self.playlists.append(val)
            elif not checked and val in self.playlists:
                self.playlists.remove(val)

            log.debug("Toggle '%s' to: %s" % (val, checked))
            return

        #FIXME: This should not run here, it should run in initialize() instead
        self.allPlaylists = self._parse_playlists(RhythmboxSource.PLAYLIST_PATH)
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"RBConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the playlists
        list_store = gtk.ListStore( gobject.TYPE_STRING,    #name
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store, preselect some playlists
        for p in self.allPlaylists:
            list_store.append( (p[0],p[0] in self.playlists) )
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
                                    active=CHECK_IDX)
                                    )

        dlg = tree.get_widget("RBConfigDialog")

        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.set_configured(True)
        dlg.destroy()

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.allPlaylists = self._parse_playlists(RhythmboxSource.PLAYLIST_PATH)
       
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        #in this case the luid for the song is its path
        songs = []
        #only consider enabled playlists
        for playlist in [p for p in self.allPlaylists if p[0] in self.playlists]:
            for song in playlist[1]:
                songs.append(song)

        return songs

    def get(self, songuri):
        DataProvider.DataSource.get(self, songuri)
        f = Audio.Audio(URI=songuri)
        f.set_UID(songuri)
        f.set_open_URI(songuri)

        return f
    def get_configuration(self):
        return { "playlists" : self.playlists }
 
    def get_UID(self):
        return ""

