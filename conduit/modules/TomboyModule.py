import dbus
import dbus.glib
import logging
log = logging.getLogger("modules.Tomboy")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.AutoSync as AutoSync
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.Utils as Utils

TOMBOY_DBUS_PATH = "/org/gnome/Tomboy/RemoteControl"
TOMBOY_DBUS_IFACE = "org.gnome.Tomboy"
TOMBOY_MIN_VERSION = "0.5.10"

MODULES = {
	"TomboyNoteTwoWay" :        { "type": "dataprovider" }
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
                log.info("Using Tomboy Version %s" % version)
                return True
            else:
                log.warn("Incompatible Tomboy Version %s" % version)
                return False
        else:
            log.warn("Tomboy DBus interface not found")
            return False

    def _update_note(self, uid, note):
        """
        @returns: A Rid for the note
        """
        log.debug("Updating note uid: %s" % uid)
        xmlContent = '<note-content version="0.1">%s\n%s</note-content>' % (note.get_title(), note.get_contents())
        ok = self.remoteTomboy.SetNoteContentsXml(uid, xmlContent)
        if not ok:
            raise Exceptions.SyncronizeError("Error setting Tomboy note content (uri: %s)" % uid)
        n = self._get_note(uid)
        return n.get_rid()

    def _get_note_mtime(self, uid):
        try:
            timestr = self.remoteTomboy.GetNoteChangeDate(uid)
            mtime = Utils.datetime_from_timestamp(int(timestr))
        except:
            log.warn("Error parsing tomboy note modification time")
            mtime = None
        return mtime

    def _get_note(self, uid):
        #Get the whole xml and strip out the tags
        log.debug("Getting note: %s" % uid)
        xmlContent=str(self.remoteTomboy.GetNoteContentsXml(uid))
        xmlContent=xmlContent.replace('<note-content version="0.1">','').replace('</note-content>','')
        title, sep, contents = xmlContent.partition("\n")
        n = Note.Note(
                title=title,
                contents=contents
                )
        n.set_UID(str(uid))
        n.set_mtime(self._get_note_mtime(uid))
        n.set_open_URI(str(uid))
        return n

    def _create_note(self, note):
        """
        @returns: A Rid for the created note
        """
        uid = self.remoteTomboy.CreateNamedNote(note.get_title())
        #fill out the note content
        rid = self._update_note(str(uid), note)
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
        existingNote = None

        log.debug("Put note LUID: %s" % LUID)

        #Check if the note, or one with same title exists
        if LUID != None:
            if self.remoteTomboy.NoteExists(LUID):
                existingNote = self._get_note(LUID)
        else:
            uid = self.remoteTomboy.FindNote(note.get_title())
            if uid != "":
                existingNote = self._get_note(str(uid))

        #compare with the existing note
        if existingNote != None:
            comp = note.compare(existingNote)
            log.debug("Comparing new %s with existing %s" % (note.get_title(),existingNote.get_title()))
            if comp == conduit.datatypes.COMPARISON_EQUAL:
                log.info("Notes are equal")
                rid = existingNote.get_rid()
            elif overwrite == True or comp == conduit.datatypes.COMPARISON_NEWER:
                log.info("Updating note")
                rid = self._update_note(LUID, note)
            else:
                raise Exceptions.SynchronizeConflictError(comp, existingNote, note)
        else:                    
            log.info("Saving new Note")
            rid = self._create_note(note)

        return rid

    def delete(self, LUID):
        if self.remoteTomboy.NoteExists(LUID):
            if self.remoteTomboy.DeleteNote(LUID):
                log.debug("Deleted note %s" % LUID)
                return

        log.warn("Error deleting note %s" % LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.notes = []

    def get_UID(self):
        return Utils.get_user_string()


