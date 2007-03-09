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

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.Module as Module
import conduit.Utils as Utils
from conduit.datatypes import DataType

from gettext import gettext as _

from conduit.DataProvider import DataSource
from conduit.DataProvider import DataSink
from conduit.DataProvider import TwoWay

import os
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.File as File

import gnomevfs
import datetime

MODULES = {
        "iPodFactory" :     { "type": "dataprovider-factory" }
}

def _string_to_unqiue_file(txt, uri, prefix, postfix=''):
    # fixme: gnomevfs is a pain :-(, this function sucks, someone make it nicer? :(
    if gnomevfs.exists(str(os.path.join(uri, prefix + postfix))):
        for i in range(1, 100):
            if False == gnomevfs.exists(str(os.path.join(uri, prefix + str(i) + postfix))):
                break
        uri = str(os.path.join(uri, prefix + str(i) + postfix))
    else:
        uri = str(os.path.join(uri, prefix + postfix))

    temp = Utils.new_tempfile(txt)
    temp.transfer(uri, True)
    return uri

class iPodFactory(Module.DataProviderFactory):
    def __init__(self, **kwargs):
        Module.DataProviderFactory.__init__(self, **kwargs)

        if kwargs.has_key("hal"):
            self.hal = kwargs["hal"]
            self.hal.connect("ipod-added", self._ipod_added)

    def probe(self):
        """ Probe for iPod's that are already attached """
        for device_type, udi, mount, name in self.hal.get_all_ipods():
            self._ipod_added(None, udi, mount, name)

    def _ipod_added(self, hal, udi, mount, name):
        """ New iPod has been discovered """
        cat = DataProvider.DataProviderCategory(
                    name,
                    "multimedia-player-ipod-video-white",
                    mount)

        for klass in [IPodNoteTwoWay, IPodContactsTwoWay, IPodCalendarTwoWay]:
            self.emit_added(
                    klass,           # Dataprovider class
                    (mount,udi,),        # Init args
                    cat)             # Category..

class IPodBase(TwoWay):
    def __init__(self, *args):
        TwoWay.__init__(self)
        self.mountPoint = args[0]
        self.uid = args[1]

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

    _name_ = _("Notes")
    _description_ = _("Sync your iPod notes")
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)

        self.dataDir = os.path.join(self.mountPoint, 'Notes')        
        self.notes = []

    def _get_shadow_dir(self):
        shadowDir = os.path.join(self.mountPoint, '.conduit')
        if not os.path.exists(shadowDir):
            os.mkdir(shadowDir)
        return shadowDir

    def _get_note_from_ipod(self, uid):
        """
        Gets a note from the ipod, considering both the shadowed copy
        and the plain text copy. If the mtimes of the two are different
        then always use the plain copy. and ignore the shadow copy
        """
        noteURI = os.path.join(self.dataDir, uid)
        noteFile = File.File(noteURI)
        rawNoteURI = os.path.join(self._get_shadow_dir(),uid)

        raw = ""
        mtime = noteFile.get_mtime()
        if os.path.exists(rawNoteURI):
            rawNoteFile = File.File(rawNoteURI)
            if mtime == rawNoteFile.get_mtime():
                raw = rawNoteFile.get_contents_as_text()

        #get the contents from the note, get the raw from the raw copy
        n = Note.Note(
                    title=uid,
                    mtime=mtime,
                    contents=noteFile.get_contents_as_text(),
                    raw=raw
                    )
        n.set_open_URI(noteURI)
        return n
    
    def _save_note_to_ipod(self, uid, note):
        """
        Save a simple iPod note in /Notes
        If the note has raw then also save that in shadowdir
        uid is the note title
        """
        ipodnote = Utils.new_tempfile(note.contents)
        ipodnote.transfer(os.path.join(self.dataDir,uid))
        if note.get_mtime() != None:
            ipodnote.force_new_mtime(note.get_mtime())

        if note.raw != "":
            shadowDir = self._get_shadow_dir()
            rawnote = Utils.new_tempfile(note.raw)
            rawnote.transfer(os.path.join(shadowDir,uid))
            if note.get_mtime() != None:
                rawnote.force_new_mtime(note.get_mtime())

    def _note_exists(self, uid):
        #Check if both the shadow copy and the ipodified version exists
        shadowDir = self._get_shadow_dir()
        return os.path.exists(os.path.join(shadowDir,uid)) and os.path.exists(os.path.join(self.dataDir,uid))
                
    def refresh(self):
        TwoWay.refresh(self)
        self.notes = []

        #Also checks directory exists
        if not os.path.exists(self.dataDir):
            os.mkdir(self.dataDir)
        
        #When acting as a source, only notes in the Notes dir are
        #considered
        for f in os.listdir(self.dataDir):
            fullpath = os.path.join(self.dataDir, f)
            if os.path.isfile(fullpath):
                self.notes.append(f)

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.notes)

    def get(self, index):
        TwoWay.get(self, index)
        uid = self.notes[index]
        return self._get_note_from_ipod(uid)

    def put(self, note, overwrite, LUID=None):
        """
        The LUID for a note in the iPod is the note title
        """
        TwoWay.put(self, note, overwrite, LUID)

        if LUID != None:
            #Check if both the shadow copy and the ipodified version exists
            if self._note_exists(LUID):
                if overwrite == True:
                    #replace the note
                    logd("Replacing Note %s" % LUID)
                    self._save_note_to_ipod(LUID, note)
                    return LUID
                else:
                    #only overwrite if newer
                    logw("OVERWRITE IF NEWER NOT IMPLEMENTED")
                    return LUID
    
        #make a new note
        logw("CHECK IF EXISTS, COMPARE, SAVE")
        self._save_note_to_ipod(note.title, note)
        return note.title
        
    def finish(self):
        self.notes = []

class IPodContactsTwoWay(IPodBase):

    _name_ = _("Contacts")
    _description_ = _("Sync your iPod contacts")
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        
        self.dataDir = os.path.join(self.mountPoint, 'Contacts')
        self.contacts = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.contacts = []

        for f in os.listdir(self.dataDir):
            fullpath = os.path.join(self.dataDir, f)
            if os.path.isfile(fullpath):
                try:
                    contact = Contact.Contact(None)
                    contact.set_from_vcard_string(open(fullpath,'r').read())
                    self.contacts.append(contact)
                except:
                    pass

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        TwoWay.get(self, index)
        return self.contacts[index]

    def put(self, contact, overwrite, LUID=None):
        TwoWay.put(self, contact, overwrite, LUID)
        _string_to_unqiue_file(str(contact), self.dataDir, 'contact')

    def finish(self):
        self.notes = None

class IPodCalendarTwoWay(IPodBase):

    _name_ = _("Calendar")
    _description_ = _("Sync your iPod calendar")
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        
        self.dataDir = os.path.join(self.mountPoint, 'Calendars')
        self.events = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.events = []

        for f in os.listdir(self.dataDir):
            fullpath = os.path.join(self.dataDir, f)
            if os.path.isfile(fullpath):
                try:
                    event = Event.Event(None)
                    event.set_from_ical_string(open(fullpath,'r').read())
                    self.events.append(event)
                except:
                    pass

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.events)

    def get(self, index):
        TwoWay.get(self, index)
        return self.events[index]

    def put(self, event, overwrite, LUID=None):
        TwoWay.put(self, event, overwrite, LUID)
        _string_to_unqiue_file(event.get_ical_string(), self.dataDir, 'event')

    def finish(self):
        self.notes = None

