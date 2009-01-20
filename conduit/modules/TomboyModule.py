import dbus
import dbus.glib
import logging
import string
log = logging.getLogger("modules.Tomboy")

import conduit
import conduit.TypeConverter as TypeConverter
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.AutoSync as AutoSync
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File
import conduit.utils as Utils

MODULES = {
	"TomboyNoteTwoWay" :        { "type": "dataprovider"    },
	"TomboyNoteConverter" :     { "type": "converter"       }
}

class TomboyNote(Note.Note):
    """
    Stores both the text and xml representations of the note
    """
    def __init__(self, title, contents, xml):
        Note.Note.__init__(self, title, contents)
        self.xml = xml
        
    def get_xml(self):
        return self.xml
        
    def __getstate__(self):
        data = Note.Note.__getstate__(self)
        data["xml"] = self.xml
        return data

    def __setstate__(self, data):
        self.xml = data["xml"]
        Note.Note.__setstate__(self, data)

class TomboyNoteConverter(TypeConverter.Converter):
    NOTE_EXTENSION = ".xml"
    ILLEGAL_TITLE_CHARS = " /"
    def __init__(self):
        self.conversions =  {
                "note,note/tomboy"  : self.note_to_tomboy_note,
                "note/tomboy,file"  : self.tomboy_note_to_file,
                "file,note/tomboy"  : self.file_to_tomboy_note,
        }
                            
    def note_to_tomboy_note(self, note, **kwargs):
        n = TomboyNote(
                title=note.get_title(),
                contents=note.get_contents(),
                xml=None
                )
        return n
        
    def tomboy_note_to_file(self, note, **kwargs):
        content = note.get_xml()
        #Old tomboy made this note, fallback to plain text
        if content == None:
            content = note.get_contents()

        #replace the following characters in the note
        #title with an underscore
        filename = note.get_title().translate(
                                        string.maketrans(
                                                self.ILLEGAL_TITLE_CHARS,
                                                "_"*len(self.ILLEGAL_TITLE_CHARS)
                                                )
                                            ) 
        f = File.TempFile(content)
        f.force_new_filename(filename)
        f.force_new_file_extension(self.NOTE_EXTENSION)
        return f
        
    def file_to_tomboy_note(self, f, **kwargs):        
        title,ext = f.get_filename_and_extension()
        text = f.get_contents_as_text()
        #A tomboy formatted XML file
        if text.startswith('<?xml version="1.0"') and text.find('xmlns="http://beatniksoftware.com/tomboy">') > 0:
            note = TomboyNote(
                    title=Utils.xml_extract_value_from_tag("title", text),
                    contents=None,
                    xml=text
                    )
        #A bog standard text file
        else:
            note = TomboyNote(
                    title=title,
                    contents=text,
                    xml=None
                    )
        return note

class TomboyNoteTwoWay(DataProvider.TwoWay, AutoSync.AutoSync):
    """
    LUID is the tomboy uid string
    """
    _name_ = "Tomboy Notes"
    _description_ = "Synchronize your Tomboy notes"
    _category_ = conduit.dataproviders.CATEGORY_NOTES
    _module_type_ = "twoway"
    _in_type_ = "note/tomboy"
    _out_type_ = "note/tomboy"
    _icon_ = "tomboy"
    _configurable_ = False
    
    TOMBOY_DBUS_PATH = "/org/gnome/Tomboy/RemoteControl"
    TOMBOY_DBUS_IFACE = "org.gnome.Tomboy"
    TOMBOY_MIN_VERSION = (0, 5, 10)
    TOMBOY_COMPLETE_XML_VERSION = (0 ,9 ,0)
    
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        AutoSync.AutoSync.__init__(self)
        self.notes = []
        self.remoteTomboy = None
        self.supportsCompleteXML = False

        self._connect_to_tomboy()

    def _connect_to_tomboy(self):
        if self.remoteTomboy != None:
            return True

        bus = dbus.SessionBus()
        if Utils.dbus_service_available(TomboyNoteTwoWay.TOMBOY_DBUS_IFACE, bus):
            obj = bus.get_object(TomboyNoteTwoWay.TOMBOY_DBUS_IFACE, TomboyNoteTwoWay.TOMBOY_DBUS_PATH)
            app = dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")
            version = tuple(int(item) for item in str(app.Version()).split('.'))
            if version >= TomboyNoteTwoWay.TOMBOY_MIN_VERSION:
                self.remoteTomboy = app
                self.remoteTomboy.connect_to_signal("NoteAdded", lambda uid: self.handle_added(str(uid)))
                self.remoteTomboy.connect_to_signal("NoteSaved", lambda uid: self.handle_modified(str(uid)))
                self.remoteTomboy.connect_to_signal("NoteDeleted", lambda uid, x: self.handle_deleted(str(uid)))
                self.supportsCompleteXML = version >= TomboyNoteTwoWay.TOMBOY_COMPLETE_XML_VERSION
                log.info("Using Tomboy Version %s" % str(version))
                return True
        return False

    def _update_note(self, uid, note):
        log.debug("Updating note uid: %s" % uid)
        if note.get_xml() != None:
            ok = self.remoteTomboy.SetNoteCompleteXml(
                                    uid,
                                    note.get_xml()
                                    )
        else:
            ok = self.remoteTomboy.SetNoteContents(
                                    uid,
                                    note.get_contents()
                                    )

        if not ok:
            raise Exceptions.SyncronizeError("Error setting Tomboy note content (uri: %s)" % uid)

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

        xml = None
        if self.supportsCompleteXML:
            xml = str(self.remoteTomboy.GetNoteCompleteXml(uid))

        n = TomboyNote(
                title=str(self.remoteTomboy.GetNoteTitle(uid)),
                contents=str(self.remoteTomboy.GetNoteContents(uid)),
                xml=xml
                )
        n.set_UID(str(uid))
        n.set_mtime(self._get_note_mtime(uid))
        n.set_open_URI(str(uid))
        return n

    def _create_note(self, note):
        uid = str(self.remoteTomboy.CreateNamedNote(note.get_title()))
        self._update_note(uid, note)
        return uid

    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.notes = []
        if self._connect_to_tomboy():
            self.notes = [str(i) for i in self.remoteTomboy.ListAllNotes()]
        else:
            raise Exceptions.RefreshError("Tomboy not available")
                
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
        log.debug("Put note LUID: %s" % LUID)

        #Check if the note, or one with same title exists
        existingNote = None
        if LUID != None:
            if self.remoteTomboy.NoteExists(LUID):
                existingNote = self._get_note(LUID)
        else:
            LUID = self.remoteTomboy.FindNote(note.get_title())
            if LUID != "":
                existingNote = self._get_note(str(LUID))

        #compare with the existing note
        if existingNote != None:
            comp = note.compare(existingNote)
            log.debug("Comparing new %s with existing %s" % (note.get_title(),existingNote.get_title()))
            if comp == conduit.datatypes.COMPARISON_EQUAL:
                log.info("Notes are equal")
            elif overwrite == True or comp == conduit.datatypes.COMPARISON_NEWER:
                log.info("Updating note")
                self._update_note(LUID, note)
            else:
                raise Exceptions.SynchronizeConflictError(comp, note, existingNote)
        else:                    
            log.info("Saving new Note")
            LUID = self._create_note(note)

        return self.get(LUID).get_rid()

    def delete(self, LUID):
        if self.remoteTomboy.NoteExists(LUID):
            if self.remoteTomboy.DeleteNote(LUID):
                log.debug("Deleted note %s" % LUID)
                return

        log.warn("Error deleting note %s" % LUID)

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        self.notes = []

    def get_UID(self):
        return Utils.get_user_string()


