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

MODULES = {
        "iPodFactory" :         { "type":   "dataprovider-factory"  }
}

try:
    import gpod
    LIBGPOD_PHOTOS = gpod.version_info >= (0,6,0)
    log.info("Module Information: %s" % Utils.get_module_information(gpod, 'version_info'))
except ImportError:
    LIBGPOD_PHOTOS = False
    log.info("iPod photo support disabled")

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
    def is_interesting(self, udi, props):
        if props.has_key("info.parent") and props.has_key("info.parent")!="":
            prop2 = self._get_properties(props["info.parent"])
            if prop2.has_key("storage.model") and prop2["storage.model"]=="iPod":
               return True
        return False

    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    kwargs['label'],
                    "multimedia-player-ipod-video-white",
                    kwargs['mount'])

    def get_dataproviders(self, udi, **kwargs):
        if LIBGPOD_PHOTOS:
            #Read information about the ipod, like if it supports 
            #photos or not
            d = gpod.itdb_device_new()
            gpod.itdb_device_set_mountpoint(d,kwargs['mount'])
            supportsPhotos = gpod.itdb_device_supports_photo(d)
            gpod.itdb_device_free(d)
            if supportsPhotos:
                return [IPodNoteTwoWay, IPodContactsTwoWay, IPodCalendarTwoWay, IPodPhotoSink]

        return [IPodNoteTwoWay, IPodContactsTwoWay, IPodCalendarTwoWay]


class IPodBase(DataProvider.TwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.mountPoint = args[0]
        self.uid = args[1]
        self.objects = None

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
    _description_ = "Sync your iPod notes"
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
    _description_ = "Sync your iPod contacts"
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
    _description_ = "Sync your iPod calendar"
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
    _description_ = "Sync your iPod photos"
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
                

