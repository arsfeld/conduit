"""
Connects to Rhythmbox with the DBus plugin

Based upon code from

Copyright 2007: John Stowers
Copyright 2008: Alexandre Rosenfeld
License: GPLv2
"""
import urllib
import os
import logging
log = logging.getLogger("modules.RhythmboxDBus")

import conduit
import conduit.Exceptions as Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
import conduit.datatypes.Audio as Audio
import dbus
try:
    import dbus.glib
except ImportError:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

from gettext import gettext as _

if Utils.program_installed("rhythmbox"):
    MODULES = {
        "RhythmboxDBusSource" :              { "type": "dataprovider" },
    }
else:
    MODULES = {}

#list store column define
NAME_IDX=0
CHECK_IDX=1

DBusPath = "com.googecode.airmindprojects.Rhythmbox"

class DBusClosedConnectionError(Exception):
    '''
    Raised when a connection to Rhythmbox doesnt exist.
    '''
    pass

class DBusConnection:
    """
    Shared connection to Rhythmbox DBus. Detects when Rhythmbox is closed and
    opened.
    """

    # Shared Rhythmbox interface
    __dbus_connection = None
    # Shared DBus Session Bus
    __session_bus = None
    # True when the DBus connection is being watched. Made to true on the first
    # instance created.
    __watch = False

    def _dbus_connect(self):
        """
        Connect to the Rhythmbox DBus object. Only availiable when Rhythmbox
        is running with the DBus plugin activated.
        """
        rb_obj = DBusConnection.__session_bus.get_object(DBusPath, "/")
        return dbus.Interface(rb_obj, DBusPath)

    def __init__(self):
        if not DBusConnection.__watch:
            def watch(name):
                '''
                Watch when the DBus connection is availiable, and connects or
                disconnects accordingly.
                '''
                if name:
                    DBusConnection.__dbus_connection = self._dbus_connect()
                else:
                    DBusConnection.__dbus_connection = None
            DBusConnection.__session_bus = dbus.SessionBus()
            # The owner changes when the plugin is activated or deactivated,
            # including when Rhythmbox starts or shutdown with the plugin active.
            DBusConnection.__session_bus.watch_name_owner(DBusPath, watch)
            DBusConnection.__watch = True


    def __getattr__(self, attr):
        """ Delegate access to DBus interface """
        if not DBusConnection:
            raise DBusClosedConnectionError()
        else:
            return getattr(DBusConnection.__dbus_connection, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to DBus interface """
        if not DBusConnection:
            raise DBusClosedConnectionError()
        else:
            return setattr(DBusConnection.__dbus_connection, attr, value)

class RhythmboxDBusSource(DataProvider.DataSource):

    _name_ = _("Rhythmbox Music (DBus)")
    _description_ = _("Synchronize songs from your Rhythmbox playlists")
    _category_ = conduit.dataproviders.CATEGORY_MEDIA
    _module_type_ = "source"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "rhythmbox"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.dbus = DBusConnection()
        #Names of the playlists we know
        self.allPlaylists = []
        #Names we wish to sync
        self.playlists = []

    def _get_playlists(self):
        return [str(p) for p in self.dbus.GetPlaylists()]

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

        self.allPlaylists = self._get_playlists()
        tree = Utils.dataprovider_glade_get_widget(
                        __file__,
                        "config.glade",
                        "RBConfigDialog")
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the playlists
        list_store = gtk.ListStore( gobject.TYPE_STRING,    #name
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store, preselect some playlists
        for p in self.allPlaylists:
            list_store.append( (p, p in self.playlists) )
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
        try:
            self.allPlaylists = self._get_playlists()
        except DBusClosedConnectionError:
            raise Exceptions.RefreshError("Could not connect to Rhythmbox")

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        try:
            # LUID is now a Rhythmbox ID, that only makes sense to Rhythmbox
            songs = []
            #only consider enabled playlists
            for playlist in [p for p in self.allPlaylists if p in self.playlists]:
                for song in self.dbus.GetPlaylistTracks(playlist):
                    songs.append(str(song))
            return songs
        except DBusClosedConnectionError:
            raise Exceptions.SyncronizeFatalError()

    def get(self, LUID):
        try:
            DataProvider.DataSource.get(self, LUID)
            songuri = str(self.dbus.GetTrackInfo(LUID, 'location'))
            f = RhythmboxAudio(URI=songuri)
            f.set_UID(LUID)
            f.set_open_URI(songuri)

            return f
        except DBusClosedConnectionError:
            raise Exceptions.SyncronizeFatalError()

    def get_configuration(self):
        return { "playlists" : self.playlists }

    def get_UID(self):
        return ""

class RhythmboxAudio(Audio.Audio):

    COVERS_PATH = os.path.expanduser("~/.gnome2/rhythmbox/covers/")

    def __init__(self, URI, **kwargs):
        Audio.Audio.__init__(self, URI, **kwargs)
        self.dbus = DBusConnection()

    def _get_info(self, info):
        try:
            return self.dbus.GetTrackInfo(self.get_UID(), info)
        except DBusClosedConnectionError:
            raise Exceptions.SyncronizeFatalError()

    def get_audio_artist(self):
        return self._get_info('artist')

    def get_audio_album(self):
        return self._get_info('album')

    def get_audio_title(self):
        return self._get_info('title')

    def get_audio_duration(self):
        '''
        Returns the audio duration in seconds
        '''
        return int(self._get_info('duration'))

    def get_audio_rating(self):
        '''
        Returns an rating from 0.0 to 5.0
        '''
        return float(self._get_info('rating'))

    # This code has been disabled in the DBus plugin
    #def set_audio_rating(self, value):
    #    self.dbus.SetTrackInfo(self.get_UID(), 'rating', value)

    def get_audio_cover_location(self):
        '''
        Returns a valid cover location or None if not availiable
        '''
        artist = self.get_audio_artist()
        album = self.get_audio_album()
        filename = str(os.path.join(RhythmboxAudio.COVERS_PATH, "%s - %s.jpg" % (artist, album)))
        if os.path.exists(filename):
            return filename
        else:
            return None
