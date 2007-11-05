try:
    import elementtree.ElementTree as ET
except:
    import xml.etree.ElementTree as ET

import dbus

import conduit
from conduit import log,logd,logw
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.AutoSync as AutoSync
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
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

class TomboyNoteTwoWay(DataProvider.TwoWay, AutoSync.AutoSync):
    """
    LUID is the tomboy uid string
    """

    _name_ = "Tomboy Notes"
    _description_ = "Sync your Tomboy notes"
    _category_ = conduit.dataproviders.CATEGORY_NOTES
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        AutoSync.AutoSync.__init__(self)
        self.notes = []
        self.bus = dbus.SessionBus()
        if self._check_tomboy_version():
            self.remoteTomboy.connect_to_signal("NoteAdded", lambda uid: self.handle_added(str(uid)))
            self.remoteTomboy.connect_to_signal("NoteSaved", lambda uid: self.handle_modified(str(uid)))
            self.remoteTomboy.connect_to_signal("NoteDeleted", lambda uid, x: self.handle_deleted(str(uid)))

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

    def _update_note(self, uid, note):
        """
        @returns: A Rid for the note
        """
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

        if not ok:
            raise Exceptions.SyncronizeError("Error setting Tomboy note content (uri: %s)" % uid)

        mtime = self._get_note_mtime(uid)
        return Rid(uid=uid, mtime=mtime, hash=mtime)

    def _get_note_mtime(self, uid):
        try:
            timestr = self.remoteTomboy.GetNoteChangeDate(uid)
            mtime = datetime.datetime.fromtimestamp(int(timestr))
        except:
            logw("Error parsing tomboy note modification time")
            mtime = None
        return mtime

    def _get_note(self, uid):
        n = Note.Note(
                    title=str(self.remoteTomboy.GetNoteTitle(uid)),
                    mtime=self._get_note_mtime(uid),
                    contents=str(self.remoteTomboy.GetNoteContents(uid)),
                    raw=str(self.remoteTomboy.GetNoteContentsXml(uid))
                    )
        n.set_UID(str(uid))
        n.set_open_URI(str(uid))
        return n

    def _create_note(self, note):
        """
        @returns: A Rid for the created note
        """
        if note.title != "":
            uid = self.remoteTomboy.CreateNamedNote(note.title)
        else:
            uid = self.remoteTomboy.CreateNote()
        #hackery because python dbus bindings dont marshal dbus.String to str
        uid = str(uid)
        if uid == "":
            raise Exceptions.SyncronizeError("Error creating Tomboy note")

        #fill out the note content
        rid = self._update_note(uid, note)
        return rid

    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.notes = []
        if self._check_tomboy_version():
            self.notes = [str(i) for i in self.remoteTomboy.ListAllNotes()]
        else:
            raise Exceptions.RefreshError
                
    def get(self, uri):
        DataProvider.TwoWay.get(self, uri)
        return self._get_note(uri)
                
    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.notes

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
                    rid = self._update_note(LUID, note)
                    return rid
                else:
                    #Only replace if newer
                    existingNote = self._get_note(LUID)
                    comp = note.compare(existingNote)
                    logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (note.title,existingNote.title,comp))
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, existingNote, note)
                    else:
                        rid = self._update_note(LUID, note)
                        return rid
            else:
                log("Told to replace note %s, nothing there to replace." % LUID)
                    
        #We havent, or its been deleted so add it. 
        log("Saving new Note")
        rid = self._create_note(note)
        return rid

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


