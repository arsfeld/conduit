"""
Provides a simple means for reading rhythmbox static playlists.

Based upon code from 

Copyright 2007: John Stowers
License: GPLv2
"""
import urllib
import os
import logging
from xml.sax import make_parser, handler, SAXException

log = logging.getLogger("modules.Rhythmbox")


try:
    import elementtree.ElementTree as ET
except:
    import xml.etree.ElementTree as ET

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
import conduit.datatypes.Audio as Audio

from gettext import gettext as _ 

if Utils.program_installed("rhythmbox"):
    MODULES = {
        "RhythmboxSource" :              { "type": "dataprovider" },
    }
else:
    MODULES = {}

#list store column define
NAME_IDX=0
CHECK_IDX=1

class SearchComplete(SAXException): pass

class RhythmboxSource(DataProvider.DataSource):

    _name_ = _("Rhythmbox Music")
    _description_ = _("Synchronize songs from your Rhythmbox playlists")
    _category_ = conduit.dataproviders.CATEGORY_MEDIA
    _module_type_ = "source"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "rhythmbox"
    _configurable_ = True

    PLAYLIST_PATH="~/.gnome2/rhythmbox/playlists.xml"
    RHYTHMDB_PATH="~/.gnome2/rhythmbox/rhythmdb.xml"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #Names of the playlists we know
        self.allPlaylists = []
        #Names we wish to sync
        self.playlists = []
        self.songdata = {}

    def _parse_playlists(self, path, allowed=[]):
        playlists = []
        songs = []
        playlist_name = _(u"Unknown")
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
                songs.append( text )

        return playlists

    def _init_songdata(self, songs):
        rb_handler = RhythmDBHandler(songs)
        parser = make_parser()
        parser.setContentHandler(rb_handler)
        path = os.path.expanduser(self.RHYTHMDB_PATH) 
        try:
            parser.parse(path)
        except SearchComplete:
            pass
        self.songdata = rb_handler.songdata
        return rb_handler.cleansongs

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
                                    active=CHECK_IDX)
                                    )

        dlg = tree.get_widget("RBConfigDialog")

        response = Utils.run_dialog (dlg, window)
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

        # get only the song data that we care about and clean up the file paths
        return self._init_songdata(songs)

    def get(self, songuri):
        DataProvider.DataSource.get(self, songuri)
        f = RhythmboxAudio(URI=songuri, songdata=self.songdata.get(songuri))
        f.set_UID(songuri)
        f.set_open_URI(songuri)

        return f

    def get_configuration(self):
        return { "playlists" : self.playlists }
 
    def get_UID(self):
        return ""

class RhythmboxAudio(Audio.Audio):
    '''Wrapper around the standard Audio datatype that implements
    the rating, playcount, and cover location tags.
    '''
    COVER_ART_PATH="~/.gnome2/rhythmbox/covers/"
    def __init__(self, URI, **kwargs):
        Audio.Audio.__init__(self, URI, **kwargs)
        self._songdata = kwargs['songdata'] or {}
        tags = {}
        # Make sure the songs has a rating (which is different from having a 0 rating)
        if 'rating' in self._songdata:
            tags['rating'] = float(self._songdata.get('rating', 0))
        tags['play_count'] = int(self._songdata.get('play-count', 0))
        tags['cover_location'] = self.find_cover_location()
        tags['title'] = self._songdata.get('title')
        tags['artist'] = self._songdata.get('artist')
        tags['album'] = self._songdata.get('album')
        tags['genre'] = self._songdata.get('genre')
        tags['track-number'] = int(self._songdata.get('track-number', 0))
        tags['duration'] = int(self._songdata.get('duration', 0)) * 1000
        tags['bitrate'] = int(self._songdata.get('bitrate', 0)) * 1000
        self.rhythmdb_tags = tags

    def find_cover_location(self):
        #TODO: Finish this
        return ''

    def get_media_tags(self):
        return self.rhythmdb_tags


class RhythmDBHandler(handler.ContentHandler):
    '''A SAX XML handler that loops through a list of songs and retrieves the interesting data.  
    While we're at it, clean the filepath and check for the existance of the file 
    before adding it to the final list of songs.

    We use a SAX parser because it's gentler on resources (it doesn't need to store the 
    entire parsed file in memory), it's *tons* faster (there is no overhead of creating
    an object tree/map), and we can stop parsing once all of the songs in the 
    list have been found.
    '''
    #we could just as easily get the rest of the file information
    _interesting_ = ('location', 'title', 'genre', 'artist', 'album', 'track-number',
        'play-count', 'rating', 'duration', 'bitrate')

    def __init__(self, searchlist):
        self.searchlist = searchlist
        self.cleansongs = []
        self.songdata = {}
        self._content_needed = ''

    def _clean_location(self, location):
        song_location = ''.join(urllib.url2pathname(location).split("://")[1:])
        if not os.path.exists(song_location):
            print "WARNING: A song referred to from the playlist '%s' cannot be found on the harddrive." % playlist_name
            return None
        return song_location

    def startElement(self, name, attrs):
        if name=='entry':
            self.song = {}
        if name in self._interesting_:
            self._content_needed = name
            
    def endElement(self, name):
        if name=='entry':
            location = self.song.get('location')
            if location in self.searchlist:
                songpath = self._clean_location(location)
                if songpath:
                    # We've found a song and it exists on the file system
                    self.cleansongs.append(songpath)
                    self.songdata[songpath] = self.song
                    self.searchlist.remove(location)
        self._content_needed = ''
        if not self.searchlist:
            raise SearchComplete('Exhausted search items.')

    def characters(self, content):
        if self._content_needed:
            self.song[self._content_needed] = content

