import gtk
import gobject
from gettext import gettext as _
from xml.dom import minidom

import logging
import conduit
import conduit.DataProvider as DataProvider
import DataType



MODULES = {
	"StickyNoteSource" : {
		"name": _("StickyNote Source"),
		"description": _("Source for synchronizing StickyNotes"),
		"type": "source",
		"category": "Notes",
		"in_type": "note",
		"out_type": "note"
	},
	"NoteDataType" : {
		"name": _("Note Data Type"),
		"description": _("Represents a users note"),
		"type": "datatype",
		"category": "",
		"in_type": "note",
		"out_type": "note",
	}
}


class StickyNoteReader(object):
    def __init__(self):
        self.doc = minidom.parse(StickyNoteReader.NOTE_FILE)
    
    def get_all_notes(self):
        notes = self.doc.documentElement.getElementsByTagName ("note")
        for n in notes:
            logging.debug("Note = %s (Modified %s)" % (n.childNodes[0].nodeValue, n.attributes["title"].nodeValue))
        
class StickyNoteSource(DataProvider.DataSource):
    NOTE_FILE = "/home/john/.gnome2/stickynotes_applet"
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("StickyNote Source"), _("Source for synchronizing StickyNotes"))
        self.icon_name = "sticky-notes"
        
        self.xml = None
        self.notes = []
        
    def initialize(self):
        DataProvider.DataProviderBase.initialize(self)    
        if self.xml is None:
            self.xml = minidom.parse(StickyNoteSource.NOTE_FILE)    
        
        try:
            notes = self.xml.documentElement.getElementsByTagName("note")
            for n in notes:
                newNote = NoteDataType()
                newNote.content = n.childNodes[0].nodeValue
                #this is not a typo, stickynotes puts the date the note was
                #created in the title attribute???
                newNote.date = n.attributes["title"].nodeValue
                #add to store
                self.notes.append(newNote)
            self.set_status(DataProvider.STATUS_DONE_INIT_OK)
        except:
            logging.warn("Error parsing note file")
            self.set_status(DataProvider.STATUS_DONE_INIT_ERROR)                

class NoteDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, _("Note Data Type"), _("Represents a users note"))
        self.conversions =  {    
                            "text,note" : self.text_to_note
                            }
                            
        #Note properties
        self.content = ""
        self.date = 0
                            
    def text_to_note(self, measure):
        return str(measure) + " was text now a note"
        
