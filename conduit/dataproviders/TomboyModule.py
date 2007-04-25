import gtk
from gettext import gettext as _

try:
    import elementtree.ElementTree as ET
except:
    import xml.etree.ElementTree as ET

import dbus


import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File
import conduit.datatypes.Text as Text
import conduit.Utils as Utils

import os
import os.path
import traceback
import datetime

TOMBOY_DBUS_PATH = "/org/gnome/Tomboy/RemoteControl"
TOMBOY_DBUS_IFACE = "org.gnome.Tomboy"
TOMBOY_MIN_VERSION = "0.5.10"

MODULES = {
	"TomboyNoteTwoWay" :    { "type": "dataprovider" }
}

class TomboyNoteTwoWay(DataProvider.TwoWay):
    """
    LUID is the tomboy uid string
    """

    _name_ = _("Tomboy Notes")
    _description_ = _("Sync your Tomboy notes")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.notes = []
        self.bus = dbus.SessionBus()

    def _check_tomboy_version(self):
        if Utils.dbus_service_available(self.bus,TOMBOY_DBUS_IFACE):
            obj = self.bus.get_object(TOMBOY_DBUS_IFACE, TOMBOY_DBUS_PATH)
            self.remoteTomboy = dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")
            version = str(self.remoteTomboy.Version())
            if version >= TOMBOY_MIN_VERSION:
                log("Using Tomboy Version %s" % version)
                return True
            else:
                logw("Incompatible Tomboy Version %s" % version)
                return False
        else:
            logw("Tomboy DBus interface not found")
            return False

    def _save_note_to_tomboy(self, uid, note):
        ok = False
        if note.raw != "":
            ok = self.remoteTomboy.SetNoteContentsXml(uid, note.raw)
        else:
            #Tomboy interprets the first line of text content as the note title
            if note.title != "":
                content = note.title+"\n"+note.contents
            else:
                content = note.contents
            ok = self.remoteTomboy.SetNoteContents(uid, content)
        return ok

    def _get_note_from_tomboy(self, uid):
        try:
            timestr = self.remoteTomboy.GetNoteChangeDate(uid)
            mtime = datetime.datetime.fromtimestamp(int(timestr))
        except:
            logw("Error parsing tomboy note modification time")
            mtime = None

        n = Note.Note(
                    title=str(self.remoteTomboy.GetNoteTitle(uid)),
                    mtime=mtime,
                    contents=str(self.remoteTomboy.GetNoteContents(uid)),
                    raw=str(self.remoteTomboy.GetNoteContentsXml(uid))
                    )
        n.set_UID(str(uid))
        n.set_open_URI(str(uid))
        return n


    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.notes = []
        if self._check_tomboy_version():
            self.notes = self.remoteTomboy.ListAllNotes()
        else:
            raise Exceptions.RefreshError
                
    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        noteURI = self.notes[index]
        return self._get_note_from_tomboy(noteURI)
                
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.notes)

    def put(self, note, overwrite, LUID=None):
        """
        Stores a Note in Tomboy.
        """
        DataProvider.TwoWay.put(self, note, overwrite, LUID)

        #Check if we have already uploaded the photo
        if LUID != None:
            if self.remoteTomboy.NoteExists(LUID):
                if overwrite == True:
                    #replace the note
                    log("Replacing Note %s" % LUID)
                    self._save_note_to_tomboy(LUID, note)
                    return LUID
                else:
                    #Only replace if newer
                    existingNote = self._get_note_from_tomboy(LUID)
                    comp = note.compare(existingNote)
                    logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (note.title,existingNote.title,comp))
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, note, existingNote)
                    else:
                        return LUID
                    
        #We havent, or its been deleted so add it. 
        log("Saving new Note")
        if note.title != "":
            uid = self.remoteTomboy.CreateNamedNote(note.title)
        else:
            uid = self.remoteTomboy.CreateNote()
        
        if uid == "":
            raise Exceptions.SyncronizeError("Error creating Tomboy note")

        if not self._save_note_to_tomboy(uid, note):
            raise Exceptions.SyncronizeError("Error setting Tomboy note content")

        return uid

    def delete(self, LUID):
        if self.remoteTomboy.NoteExists(LUID):
            if self.remoteTomboy.DeleteNote(LUID):
                logd("Deleted note %s" % LUID)
                return

        logw("Error deleting note %s" % LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.notes = []

    def get_UID(self):
        return Utils.get_user_string()


