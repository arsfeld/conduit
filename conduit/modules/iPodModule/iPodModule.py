"""
Provides a number of dataproviders which are associated with
removable devices such as USB keys.

It also includes classes specific to the ipod.
This file is not dynamically loaded at runtime in the same
way as the other dataproviders as it needs to be loaded all the time in
order to listen to HAL events

Copyright: John Stowers, 2006
License: GPLv2
"""
import os
import pickle
import logging
import time
import socket
import locale
import weakref
import threading
import gobject
log = logging.getLogger("modules.iPod")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.VolumeFactory as VolumeFactory
import conduit.utils as Utils
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.File as File
import conduit.datatypes.Audio as Audio
import conduit.datatypes.Video as Video

from gettext import gettext as _

errormsg = ""
try:
    import gpod
    if gpod.version_info >= (0,6,0):
        MODULES = {
            "iPodFactory" :         { "type":   "dataprovider-factory"  },
        }
        log.info("Module Information: %s" % Utils.get_module_information(gpod, 'version_info'))
    MEDIATYPE_MUSICVIDEO = gpod.ITDB_MEDIATYPE_MUSICVIDEO
    MEDIATYPE_MOVIE = gpod.ITDB_MEDIATYPE_MOVIE
    MEDIATYPE_TVSHOW = gpod.ITDB_MEDIATYPE_TVSHOW
    MEDIATYPE_AUDIO = gpod.ITDB_MEDIATYPE_AUDIO
    MEDIATYPE_PODCAST = gpod.ITDB_MEDIATYPE_PODCAST
except ImportError:
    errormsg = "iPod support disabled"
except locale.Error:
    errormsg = "iPod support disabled (Incorrect locale)"

if errormsg:
    MODULES = {}
    log.info(errormsg)
    MEDIATYPE_MUSICVIDEO = 0
    MEDIATYPE_MOVIE = 1
    MEDIATYPE_TVSHOW = 2
    MEDIATYPE_AUDIO = 3
    MEDIATYPE_PODCAST = 4

def _string_to_unqiue_file(txt, base_uri, prefix, postfix=''):
    for i in range(1, 10000):
        filename = prefix + str(i) + postfix
        uri = os.path.join(base_uri, filename)
        f = File.File(uri)
        if not f.exists():
            break

    temp = Utils.new_tempfile(txt)
    temp.transfer(uri, True)
    temp.set_UID(filename)
    return temp.get_rid()

class iPodFactory(VolumeFactory.VolumeFactory):

    def _get_mount_path(self, props):
        return str(props["volume.mount_point"])

    def is_interesting(self, udi, props):
        if props.get("info.parent"):
            parent = self._get_properties(props["info.parent"])
            if parent.get("storage.model") == "iPod":
                props.update(parent)
                return True
        return False

    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    kwargs['volume.label'],
                    "multimedia-player-ipod-standard-color",
                    self._get_mount_path(kwargs))

    def get_dataproviders(self, udi, **kwargs):
        #Read information about the ipod, like if it supports
        #photos or not
        d = gpod.itdb_device_new()
        gpod.itdb_device_set_mountpoint(d,self._get_mount_path(kwargs))
        supportsPhotos = gpod.itdb_device_supports_photo(d)
        gpod.itdb_device_free(d)
        if supportsPhotos:
            return [IPodMusicTwoWay, IPodVideoTwoWay, IPodNoteTwoWay, IPodContactsTwoWay, IPodCalendarTwoWay, IPodPhotoSink]
        else:
            log.info("iPod does not report photo support")
            return [IPodMusicTwoWay, IPodVideoTwoWay, IPodNoteTwoWay, IPodContactsTwoWay, IPodCalendarTwoWay]

    def get_args(self, udi, **kwargs):
        """
        iPod needs a local path to the DB, not a URI
        """
        kwargs["mount_path"] = self._get_mount_path(kwargs)
        return (kwargs['mount_path'], udi)

class IPodBase(DataProvider.TwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.mountPoint = args[0]
        self.uid = args[1]
        self.objects = None

        log.debug("Created ipod %s at %s" % (self.__class__.__name__, self.mountPoint))

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.objects = []

        #Also checks directory exists
        if not os.path.exists(self.dataDir):
            os.mkdir(self.dataDir)

        #When acting as a source, only notes in the Notes dir are
        #considered
        for f in os.listdir(self.dataDir):
            fullpath = os.path.join(self.dataDir, f)
            if os.path.isfile(fullpath):
                self.objects.append(f)

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.objects

    def delete(self, LUID):
        obj = File.File(URI=os.path.join(self.dataDir, LUID))
        if obj.exists():
            obj.delete()

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        self.objects = None

    def get_UID(self):
        return self.uid

    def _get_unique_filename(self, directory):
        """
        Returns the name of a non-existant file on the
        ipod within directory

        @param directory: Name of the directory within the device root to make
        the random file in
        """
        done = False
        while not done:
            f = os.path.join(self.mountPoint,directory,Utils.random_string())
            if not os.path.exists(f):
                done = True
        return f

class IPodNoteTwoWay(IPodBase):
    """
    Stores Notes on the iPod.
    Rather than requiring a perfect transform to and from notes to the
    ipod note format I also store the original note data in a
    .conduit directory in the root of the iPod.

    Notes are saved as title.txt and a copy of the raw note is saved as
    title.note

    LUID is the note title
    """

    _name_ = "Notes"
    _description_ = "Synchronize your iPod notes"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    # datatypes.Note doesn't care about encoding,
    # lets be naive and assume that all notes are utf-8
    ENCODING_DECLARATION = '<?xml encoding="utf-8"?>'

    def __init__(self, *args):
        IPodBase.__init__(self, *args)

        self.dataDir = os.path.join(self.mountPoint, 'Notes')
        self.objects = []

    def _get_shadow_dir(self):
        shadowDir = os.path.join(self.mountPoint, '.conduit')
        if not os.path.exists(shadowDir):
            os.mkdir(shadowDir)
        return shadowDir

    def _get_note_from_ipod(self, uid):
        """
        Gets a note from the ipod, If the pickled shadow copy exists
        then return that
        """
        rawNoteURI = os.path.join(self._get_shadow_dir(),uid)
        if os.path.exists(rawNoteURI):
            raw = open(rawNoteURI,'rb')
            try:
                n = pickle.load(raw)
                raw.close()
                return n
            except:
                raw.close()

        noteURI = os.path.join(self.dataDir, uid)
        noteFile = File.File(URI=noteURI)
        #get the contents from the note, get the raw from the raw copy.
        #the UID for notes from the ipod is the filename
        n = Note.Note(
                    title=uid,
                    contents=noteFile.get_contents_as_text().replace(
                        self.ENCODING_DECLARATION, '', 1),
                    )
        n.set_UID(uid)
        n.set_mtime(noteFile.get_mtime())
        n.set_open_URI(noteURI)
        return n

    def _save_note_to_ipod(self, uid, note):
        """
        Save a simple iPod note in /Notes
        If the note has raw then also save that in shadowdir
        uid is the note title.
        """
        # the normal note viewed by the iPod
        # inject an encoding declaration if it is missing.
        contents = note.get_contents()
        if not self.ENCODING_DECLARATION in contents:
            contents = ''.join([self.ENCODING_DECLARATION, contents])
        ipodnote = Utils.new_tempfile(contents)

        ipodnote.transfer(os.path.join(self.dataDir,uid), overwrite=True)
        ipodnote.set_mtime(note.get_mtime())
        ipodnote.set_UID(uid)

        #the raw pickled note for sync
        raw = open(os.path.join(self._get_shadow_dir(),uid),'wb')
        pickle.dump(note, raw, -1)
        raw.close()

        return ipodnote.get_rid()

    def _note_exists(self, uid):
        #Check if both the shadow copy and the ipodified version exists
        shadowDir = self._get_shadow_dir()
        return os.path.exists(os.path.join(shadowDir,uid)) and os.path.exists(os.path.join(self.dataDir,uid))

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self._get_note_from_ipod(LUID)

    def put(self, note, overwrite, LUID=None):
        """
        The LUID for a note in the iPod is the note title
        """
        DataProvider.TwoWay.put(self, note, overwrite, LUID)

        if LUID != None:
            #Check if both the shadow copy and the ipodified version exists
            if self._note_exists(LUID):
                if overwrite == True:
                    #replace the note
                    log.debug("Replacing Note %s" % LUID)
                    return self._save_note_to_ipod(LUID, note)
                else:
                    #only overwrite if newer
                    log.warn("OVERWRITE IF NEWER NOT IMPLEMENTED")
                    return self._save_note_to_ipod(LUID, note)

        #make a new note
        log.warn("CHECK IF EXISTS, COMPARE, SAVE")
        return self._save_note_to_ipod(note.title, note)

    def delete(self, LUID):
        IPodBase.delete(self, LUID)

        raw = File.File(URI=os.path.join(self._get_shadow_dir(), LUID))
        if raw.exists():
            raw.delete()

class IPodContactsTwoWay(IPodBase):

    _name_ = "Contacts"
    _description_ = "Synchronize your iPod contacts"
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        self.dataDir = os.path.join(self.mountPoint, 'Contacts')

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        fullpath = os.path.join(self.dataDir, LUID)
        f = File.File(URI=fullpath)

        contact = Contact.Contact()
        contact.set_from_vcard_string(f.get_contents_as_text())
        contact.set_open_URI(fullpath)
        contact.set_mtime(f.get_mtime())
        contact.set_UID(LUID)
        return contact

    def put(self, contact, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, contact, overwrite, LUID)

        if LUID != None:
            f = Utils.new_tempfile(contact.get_vcard_string())
            f.transfer(os.path.join(self.dataDir, LUID), overwrite=True)
            f.set_UID(LUID)
            return f.get_rid()

        return _string_to_unqiue_file(contact.get_vcard_string(), self.dataDir, 'contact')

class IPodCalendarTwoWay(IPodBase):

    _name_ = "Calendar"
    _description_ = "Synchronize your iPod calendar"
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        self.dataDir = os.path.join(self.mountPoint, 'Calendars')

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        fullpath = os.path.join(self.dataDir, LUID)
        f = File.File(URI=fullpath)

        event = Event.Event()
        event.set_from_ical_string(f.get_contents_as_text())
        event.set_open_URI(fullpath)
        event.set_mtime(f.get_mtime())
        event.set_UID(LUID)
        return event

    def put(self, event, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, event, overwrite, LUID)

        if LUID != None:
            f = Utils.new_tempfile(event.get_ical_string())
            f.transfer(os.path.join(self.dataDir, LUID), overwrite=True)
            f.set_UID(LUID)
            return f.get_rid()

        return _string_to_unqiue_file(event.get_ical_string(), self.dataDir, 'event')

class IPodPhotoSink(IPodBase):

    _name_ = "Photos"
    _description_ = "Synchronize your iPod photos"
    _module_type_ = "sink"
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"
    _icon_ = "image-x-generic"
    _configurable_ = True

    SAFE_PHOTO_ALBUM = "Photo Library"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        self.db = gpod.PhotoDatabase(self.mountPoint)
        self.albumName = "Conduit"
        self.album = None

    def _set_sysinfo(self, modelnumstr, model):
        gpod.itdb_device_set_sysinfo(self.db._itdb.device, modelnumstr, model)

    def _get_photo_album(self, albumName):
        for album in self.db.PhotoAlbums:
            if album.name == albumName:
                log.debug("Found album: %s" % albumName)
                return album

        log.debug("Creating album: %s" % albumName)
        return self._create_photo_album(albumName)

    def _create_photo_album(self, albumName):
        if albumName in [a.name for a in self.db.PhotoAlbums]:
            log.warn("Album already exists: %s" % albumName)
            album = self._get_photo_album(albumName)
        else:
            album = self.db.new_PhotoAlbum(title=albumName)
        return album

    def _get_photo_by_id(self, id):
        for album in self.db.PhotoAlbums:
            for photo in album:
                if str(photo['id']) == str(id):
                    return photo
        return None

    def _delete_album(self, albumName):
        if albumName == self.SAFE_PHOTO_ALBUM:
            log.warn("Cannot delete album: %s" % self.SAFE_PHOTO_ALBUM)
        else:
            album = self._get_photo_album(albumName)
            for photo in album[:]:
                album.remove(photo)
            self.db.remove(album)

    def _empty_all_photos(self):
        for photo in self.db.PhotoAlbums[0][:]:
            self.db.remove(photo)

    def _get_photo_albums(self):
        i = []
        for album in self.db.PhotoAlbums:
            i.append(album.name)
        return i

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.album = self._get_photo_album(self.albumName)

    def get_all(self):
        uids = []
        for photo in self.album:
            uids.append(str(photo['id']))
        return uids

    def put(self, f, overwrite, LUID=None):
        photo = self.db.new_Photo(filename=f.get_local_uri())
        self.album.add(photo)
        gpod.itdb_photodb_write(self.db._itdb, None)
        return conduit.datatypes.Rid(str(photo['id']), None, hash(None))

    def delete(self, LUID):
        photo = self._get_photo_by_id(LUID)
        if photo != None:
            self.db.remove(photo)
            gpod.itdb_photodb_write(self.db._itdb, None)

    def configure(self, window):
        import gobject
        import gtk
        def build_album_model(albumCombo):
            self.album_store.clear()
            album_count = 0
            album_iter = None
            for name in self._get_photo_albums():
                iter = self.album_store.append((name,))
                if name == self.albumName:
                    album_iter = iter
                album_count += 1

            if album_iter:
                albumCombo.set_active_iter(album_iter)
            elif self.albumName:
                albumCombo.child.set_text(self.albumName)
            elif album_count:
                albumCombo.set_active(0)

        def delete_click(sender, albumCombo):
            albumName = albumCombo.get_active_text()
            if albumName:
                self._delete_album(albumName)
                build_album_model(albumCombo)

        #get a whole bunch of widgets
        tree = Utils.dataprovider_glade_get_widget(
                        __file__,
                        "config.glade",
                        "PhotoConfigDialog")
        albumCombo = tree.get_widget("album_combobox")
        delete_button = tree.get_widget("delete_button")

        #setup album store
        self.album_store = gtk.ListStore(gobject.TYPE_STRING)
        albumCombo.set_model(self.album_store)
        cell = gtk.CellRendererText()
        albumCombo.pack_start(cell, True)
        albumCombo.set_text_column(0)

        #setup widgets
        build_album_model(albumCombo)
        delete_button.connect('clicked', delete_click, albumCombo)

        # run dialog
        dlg = tree.get_widget("PhotoConfigDialog")
        response = Utils.run_dialog(dlg, window)

        if response == True:
            #get the values from the widgets
            self.albumName = albumCombo.get_active_text()
        dlg.destroy()

        del self.album_store

    def is_configured (self, isSource, isTwoWay):
        return len(self.albumName) > 0

    def uninitialize(self):
        self.db.close()

unicode_conv = lambda v: unicode(v).encode('UTF-8','replace')

class IPodFileBase:
    '''
    A wrapper around an iPod track. iPod track properties are converted into
    Media properties, and vice-versa.
    '''
    
    #Mappings from the Media metadata to the iPod metadata and vice-versa, 
    #including type-checking
    media_to_ipod = {
        'title' : ('title', unicode_conv),
        'artist' : ('artist', unicode_conv),
        'album' : ('album', unicode_conv),
        'composer' : ('composer', unicode_conv),
        'rating' : ('rating', lambda v: float(v) / 0.05),
        'genre' : ('genre', unicode_conv),
        'track_nr' : ('track-number', int),
        'tracks' : ('track-count', int),
        'bitrate' : ('bitrate', int),
        'tracklen' : ('duration', int),
        'samplerate' : ('samplerate', int),
        'width' : ('width', int),
        'height' : ('height', int),
    }
    
    ipod_to_media = {
        'title' : ('title', unicode_conv),
        'artist' : ('artist', unicode_conv),
        'album' : ('album', unicode_conv),
        'composer' : ('composer', unicode_conv),
        'rating' : ('rating', lambda v: float(v) * 0.05),
        'genre' : ('genre', unicode_conv),
        'track-number' : ('track_nr', int),
        'track-count' : ('tracks', int),
        'bitrate' : ('bitrate', int),
        'duration' : ('tracklen', int),
        'samplerate' : ('samplerate', int),
        'width' : ('width', int),
        'height' : ('height', int),        
    }

    def __init__(self, db, track = None, f = None):
        '''
        Wraps an iPod track in a Datatype. 
        Passing a file creates a new track in the iPod db, with media information 
        from that file. Use copy_ipod to transfer it into the iPod.
        Passing an existing iPod track exports the track's information as a 
        Media datatype.
        
        @param ipod_track: An iPod track to wrap
        @param f: A File to extract the information from
        '''
        self.db = db
        if track:
            self.track = track
        else:
            self.track = self.db.new_Track()
        if f:
            self.set_info_from_file(f)
        
    def get_UID(self):
        '''
        Returns the database ID (usually a random number, which is always valid
        for this track in this db, even across application restarts)
        '''
        return str(self.track['dbid'])

    def _convert_tags(self, from_tags, mapping):
        '''
        Convert from one mapping to another.
        Returns an iterator with (name, value) for each tag in from_tags
        '''
        for from_name, from_value in from_tags.iteritems():
            if from_name in mapping:
                to_name, to_converter = mapping[from_name]
                try:
                    to_value = to_converter(from_value)
                    yield to_name, to_value
                except Exception, e:
                    log.warn("Could not convert property %s: %s as %s. (Error: %s)" % (from_name, from_value, to_converter, e))

    def set_info_from_file(self, f):
        '''
        Get the track information from a file, including the metadata.
        Works best with GStreamer metadata in MediaFile.
        '''
        tags = f.get_media_tags()
        for name, value in self._convert_tags(tags, self.media_to_ipod):
            log.debug("Got %s = %s" % (name, value))
            self.track[name] = value
        #Make sure we have a title to this song, even if it's just the filename
        if self.track['title'] is None:
            self.track['title'] = os.path.basename(f.get_local_uri())
        self.track['time_modified'] = os.stat(f.get_local_uri()).st_mtime
        self.track['time_added'] = int(time.time())
        self.track['userdata'] = {'transferred': 0,
                                  'hostname': socket.gethostname(),
                                  'charset': locale.getpreferredencoding()}
        self.track._set_userdata_utf8('filename', f.get_local_uri())
        
    def get_track_filename(self):
        filename = self.track.ipod_filename()
        if not filename or not os.path.exists(filename):
            filename = self.track._userdata_into_default_locale('filename')
        return filename
        
    def get_media_tags(self):
        '''
        Extends the MediaFile class to include the iPod metadata, instead of
        calling the GStreamer loader. It's much faster this way, and provides
        some nice information to other dataproviders, like ratings.
        '''
        #FIXME: Cache this information
        
        #Get the information from the iPod track.
        #The track might look like a dict, but it isnt, so we make it into one.
        track_tags = dict([(name, track[name]) for name in self.media_to_ipod.keys()])
        return dict(self._convert_tags(track_tags, self.ipod_to_media))

    #FIXME: Remove this. Use native operations from Conduit instead.
    #       We would have to define the transfered userdata as 1 and then call
    #       Conduit to copy the file. 
    #       But that is Conduit's copy file way?
    def copy_ipod(self):
        self.track.copy_to_ipod()

class IPodAudio(IPodFileBase, Audio.Audio):
    def __init__(self, *args, **kwargs):
        '''
        Initialize a new Audio track for this db and file.
        '''
        IPodFileBase.__init__(self, *args, **kwargs)
        Audio.Audio.__init__(self, URI = self.get_track_filename())

    def set_info_from_file(self, audio):
        IPodFileBase.set_info_from_file(self, audio)
        self.track['mediatype'] = gpod.ITDB_MEDIATYPE_AUDIO
        cover_location = audio.get_audio_cover_location()
        if cover_location:
            self.track.set_coverart_from_file(str(cover_location))

class IPodVideo(IPodFileBase, Video.Video):
    def __init__(self, *args, **kwargs):
        '''
        Initialize a new Video track for this db and file.
        '''
        IPodFileBase.__init__(self, *args, **kwargs)
        Video.Video.__init__(self, URI = self.get_track_filename())
        
        log.debug('Video kind selected: %s' % (kwargs['video_kind']))
        self.video_kind = kwargs['video_kind']
        
    def set_info_from_file(self, video):
        IPodFileBase.set_info_from_file(video)
        self.track['mediatype'] = {'movie': MEDIATYPE_MOVIE,
                                   'musicvideo': MEDIATYPE_MUSICVIDEO,
                                   'tvshow': MEDIATYPE_TVSHOW,
                                   'podcast': MEDIATYPE_PODCAST
                                   } [self.video_kind]

class DBCache:
    '''
    Keeps a list of open GPod databases.

    Keeps one database open for each mount-point.
    Automatically disposes unused databases.
    '''
    __db_list = weakref.WeakValueDictionary()
    __db_locks = weakref.WeakKeyDictionary()
    __lock = threading.Lock()

    @classmethod
    def get_db(self, mount_point):
        self.__lock.acquire()
        try:
            if mount_point in self.__db_list:
                log.debug('Getting DB in cache for %s' % (mount_point))
                db = self.__db_list[mount_point]
            else:
                if mount_point:
                    log.debug('Creating DB for %s' % mount_point)
                    db = gpod.Database(mount_point)
                else:
                    log.debug('Creating local DB')
                    db = gpod.Database(local=True)
                self.__db_list[mount_point] = db
                self.__db_locks[db] = threading.Lock()
            return db
        finally:
            self.__lock.release()

    @classmethod
    def release_db(self, db):
        assert db in self.__db_locks
        # We dont do nothing here yet, but we could use to release resources.
        # The db is automatically removed from the list because of the weak 
        # reference.
        log.debug('Releasing DB for %s' % db)

    @classmethod
    def lock_db(self, db):
        assert db in self.__db_locks
        log.debug('Locking DB %s' % db)
        self.__db_locks[db].acquire()

    @classmethod
    def unlock_db(self, db):
        assert db in self.__db_locks
        log.debug('Unlocking DB %s' % db)
        self.__db_locks[db].release()

class IPodMediaTwoWay(IPodBase):
    FORMAT_CONVERSION_STRING = _("Encoding")

    def __init__(self, *args):
        self.local_db = (len(args) == 0)
        if not self.local_db:
            IPodBase.__init__(self, *args)
        else:
            # Use local database for testing
            DataProvider.TwoWay.__init__(self)        
            self.uid = "Local"
        self.db = None
        #self.tracks = {}
        self.tracks_id = {}
        self.track_args = {}
        self.keep_converted = True
        
    def get_db(self):
        if self.db:
            DBCache.lock_db(self.db)
            return self.db
        if not self.local_db:
            self.db = DBCache.get_db(self.mountPoint)
        else:
            self.db = DBCache.get_db(None)        
        DBCache.lock_db(self.db)
        return self.db
    
    def unlock_db(self):
        DBCache.unlock_db(self.db)
        
    def release_db(self):
        if not self.db:
            return
        self.db.close()
        DBCache.release_db(self.db)
        self.db = None        

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.tracks = {}
        self.tracks_id = {}
        self.get_db()
        try:
            def add_track(track):
                self.tracks_id[str(track['dbid'])] = track
            [add_track(track) for track in self.db \
                if track['mediatype'] in self._mediatype_]
        finally:
            self.unlock_db()

    def get_all(self):
        return self.tracks_id.keys()

    def get(self, LUID = None):
        self.get_db()
        try:
            if LUID not in self.tracks_id:
                raise Exceptions.SyncronizeError('Track ID %s not found in iPod DB %s' % (LUID, self.db))
            track = self.tracks_id[LUID]
            ipod_file = self._ipodmedia_(self.db, track = track)
            filename = ipod_file.get_track_filename()
            if not os.path.exists(filename):
                raise Exceptions.SyncronizeError("Could not find iPod track file %s" % (filename))
            #Set a nice "Artist - Title" name with the original filename
            #extension
            #FIXME: Doesnt work as expected anymore, the original filename is
            #renamed instead
            #if track.ipod_filename() and track['artist'] and track['title']:
            #    ipod_file.force_new_filename("%(artist)s - %(title)s" % track + \
            #        os.path.splitext(filename)[1])
            return ipod_file
        finally:
            self.unlock_db()
        return None

    def put(self, f, overwrite, LUID=None):
        self.get_db()
        try:
            media_file = self._ipodmedia_(db = self.db, f = f, **self.track_args)
            #FIXME: We keep the db locked while we copy the file. Not good
            #media_file.
            media_file.copy_ipod()
            self.tracks_id[str(media_file.track['dbid'])] = media_file.track
            #FIXME: Writing the db here is for debug only. Closing does not actually
            # close the db, it only writes it's contents to disk.            
            # Sometimes, if we only close the db when the sync is over, it might
            # take a long time to close the db, because many files are being 
            # copied to the iPod. Closing the DB every time not only keeps
            # this time small, but also keeps the db more consistent in case of 
            # a crash. But it also incurs a big overhead. 
            # Maybe a batch update could be a better solution (close after 5 tracks?)
            self.db.close()
            return media_file
        finally:
            self.unlock_db()

    def delete(self, LUID):
        track = self.tracks_id[LUID]
        if track:
            self.get_db()
            try:
                self.db.remove(track)
                self.db.close()
            finally:
                self.unlock_db()

    def get_config_items(self):
        import gtk
        #Get an array of encodings, so it can be indexed inside a combobox
        self.config_encodings = tuple(self.encodings.iteritems())
        initial_enc = None
        for (encoding_name, encoding_opts) in self.config_encodings:
            if encoding_name == self.encoding:
                initial_enc = encoding_opts.get('description', None) or encoding_name

        def selectEnc(index, text):
            self.encoding = self.config_encodings[index][0]
            log.debug('Encoding %s selected' % self.encoding)
        
        def selectKeep(value):
            self.keep_converted = value
            log.debug("Keep converted selected: %s" % (value))
        
        return [
                    {
                    "Name" : self.FORMAT_CONVERSION_STRING,
                    "Kind" : "list",
                    "Callback" : selectEnc,
                    "Values" : [enc_opts.get('description', None) or enc_name for enc_name, enc_opts in self.config_encodings],
                    "InitialValue" : initial_enc
                    },
                    
                    {"Name" : _("Keep converted files"),
                     "Kind" : "check",
                     "Callback" : selectKeep,
                     "InitialValue" : self.keep_converted
                    },
                ]        

    def configure(self, window):
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, self.get_config_items())
        dialog.run()

    def set_configuration(self, config):
        if 'encoding' in config:
            self.encoding = config['encoding']
        if 'keep_converted' in config:
            self.keep_converted = config['keep_converted']

    def get_configuration(self):
        return {'encoding':self.encoding,
                'keep_converted': self.keep_converted}

    def get_input_conversion_args(self):
        try:
            args = self.encodings[self.encoding]
            # FIXME
            # If we pass the bool in the args, it will become a string, and 
            # will always return True later in the converter.
            # So we only pass it if is True. When it's False, not being there
            # tells the converter it isn't True.
            # I'm not sure it was supposed to work like this.
            if self.keep_converted:
                args['keep_converted'] = True
            return args
        except KeyError:
            return {}

    def uninitialize(self):
        self.release_db()

IPOD_AUDIO_ENCODINGS = {
    "mp3": {"description": "Mp3", "acodec": "lame", "file_extension": "mp3"},
    #FIXME: AAC needs a MP4 mux
    #"aac": {"description": "AAC", "acodec": "faac", "file_extension": "m4a"},
    }

class IPodMusicTwoWay(IPodMediaTwoWay):

    _name_ = "iPod Music"
    _description_ = "Synchronize your iPod music"
    _module_type_ = "twoway"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "audio-x-generic"
    _configurable_ = True

    _mediatype_ = (MEDIATYPE_AUDIO,)
    _ipodmedia_ = IPodAudio

    def __init__(self, *args):
        IPodMediaTwoWay.__init__(self, *args)
        self.encodings = IPOD_AUDIO_ENCODINGS
        self.encoding = 'aac'

IPOD_VIDEO_ENCODINGS = {
    #FIXME: Add iPod mpeg4 restrictions. Follow:
    # http://rob.opendot.cl/index.php/useful-stuff/ffmpeg-x264-encoding-guide/
    "mp4_x264":{"description": "MP4 (Better quality - H.264)","vcodec":"x264enc", "acodec":"faac", 
        "format":"ffmux_mp4", "file_extension":"m4v", "width": 320, "height": 240, 
        "mimetype": "video/mp4"},
    #FIXME: Two-pass encoding is not working. The first pass never finishes.
    #"mp4_x264_twopass":{"description": "MP4 (H.264, Two-pass EXPERIMENTAL)", 
    #    "vcodec_pass1":"x264enc pass=1", "vcodec_pass2":"x264enc pass=2", 
    #    "acodec":"faac", "format":"ffmux_mp4", "file_extension":"m4v", 
    #    "width": 320, "height": 240, "mimetype": "video/mp4", 'twopass':True},
    "mp4_xvid":{"description": "MP4 (Faster conversion - XVid)","vcodec":"ffenc_mpeg4", "acodec":"faac",
        "format":"ffmux_mp4", "file_extension":"m4v", "width": 320, "height": 240, 
        "mimetype": "video/mp4"},
    }

class IPodVideoTwoWay(IPodMediaTwoWay):

    _name_ = "iPod Video"
    _description_ = "Synchronize your iPod videos"
    _module_type_ = "twoway"
    _in_type_ = "file/video"
    _out_type_ = "file/video"
    _icon_ = "video-x-generic"
    _configurable_ = True

    _mediatype_ = (MEDIATYPE_MUSICVIDEO, MEDIATYPE_MOVIE, MEDIATYPE_TVSHOW)
    _ipodmedia_ = IPodVideo

    def __init__(self, *args):
        IPodMediaTwoWay.__init__(self, *args)
        self.encodings = IPOD_VIDEO_ENCODINGS
        self.encoding = 'mp4_x264'
        self.video_kind = 'movie'
        self._update_track_args()
        
    def _update_track_args(self):
        self.track_args['video_kind'] = self.video_kind

    def get_config_items(self):
        video_kinds = [('Movie', 'movie'), 
                       ('Music Video', 'musicvideo'),
                       ('TV Show', 'tvshow')]
        initial = None
        for description, name in video_kinds:
            if name == self.video_kind:
                initial = description

        def selectKind(index, text):
            self.video_kind = video_kinds[index][1]
            self._update_track_args()

        items = IPodMediaTwoWay.get_config_items(self)
        items.append( 
                        {
                            "Name" : "Video Kind",
                            "Kind" : "list",
                            "Callback" : selectKind,
                            "Values" : [description for description, name in video_kinds],
                            "InitialValue" : initial
                        } 
                    )             
                    
        return items
    
    def set_configuration(self, config):
        IPodMediaTwoWay.set_configuration(self, config)
        if 'video_kind' in config:
            self.video_kind = config['video_kind']
        self._update_track_args()

    def get_configuration(self):
        config = IPodMediaTwoWay.get_configuration(self)
        config.update({'video_kind':self.video_kind})
        return config
