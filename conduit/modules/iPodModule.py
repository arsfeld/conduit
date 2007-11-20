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

import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.VolumeFactory as VolumeFactory
import conduit.Utils as Utils
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.File as File

MODULES = {
        "iPodFactory" :         { "type":   "dataprovider-factory"  }
}

#try:
#    import gpod
#    LIBGPOD_PHOTOS = True
#except:
#    LIBGPOD_PHOTOS = False

def _string_to_unqiue_file(txt, uri, prefix, postfix=''):
    for i in range(1, 10000):
        filename = prefix + str(i) + postfix
        uri = os.path.join(uri, filename)
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

    def finish(self):
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

    _name_ = "iPod Notes"
    _description_ = "Sync your iPod notes"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

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
                    contents=noteFile.get_contents_as_text(),
                    )
        n.set_UID(uid)
        n.set_mtime(noteFile.get_mtime())
        n.set_open_URI(noteURI)
        return n
    
    def _save_note_to_ipod(self, uid, note):
        """
        Save a simple iPod note in /Notes
        If the note has raw then also save that in shadowdir
        uid is the note title
        """
        #the normal note viewed by the ipod
        ipodnote = Utils.new_tempfile(note.get_contents())
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

    _name_ = "iPod Contacts"
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

        contact = Contact.Contact(None)
        contact.set_from_vcard_string(f.get_contents_as_text())
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

        event = Event.Event(None)
        event.set_from_ical_string(f.get_contents_as_text())
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

#class IPodPhotoTwoWay(IPodBase):
#
#    _name_ = "Photos"
#    _description_ = "Sync your iPod photos"
#    _module_type_ = "twoway"
#    _in_type_ = "file/photo"
#    _out_type_ = "file/photo"
#    _icon_ = "image-x-generic"
#
#    def __init__(self, *args):
#        IPodBase.__init__(self, *args)
#        self.dataDir = os.path.join(self.mountPoint, 'Photos')
#        self.uids = None
#
#    def refresh(self):
#        DataProvider.TwoWay.refresh(self)
#        self.db = gpod.PhotoDatabase(self.mountPoint)
#        self.uids = []
#
#        for photo in self.db.PhotoAlbums[0]:
#            self.uids.append(photo.id)
#
#    def get_all(self):
#        return self.uids
#
#    def get(self, LUID):
#        photopath = os.path.join(self.dataDir, LUID)
#        f = File.File(URI=photopath)
#        f.set_open_URI(photopath)
#        f.set_UID(photopath)
#        return f
#
#    def put(self, obj, overwrite, LUID=None):
#        photo = self.db.new_Photo(filename=obj.URI)
#        return Rid(uid=photo.id, mtime="", hash="")
#
#    def delete(self, LUID):
#        self.db.remove(self.get(LUID))
#
#    def finish(self):
#        self.uids = None
#
