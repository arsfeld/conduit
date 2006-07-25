import gtk
from gettext import gettext as _
from xml.dom import minidom

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes.Note as Note

MODULES = {
	"StickyNoteSource" : {
		"name": _("StickyNote Source"),
		"description": _("Source for synchronizing StickyNotes"),
		"type": "source",
		"category": "Notes",
		"in_type": "note",
		"out_type": "note"
	},
	"NoteConverter" : {
		"name": _("Note Data Type"),
		"description": _("Represents a users note"),
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": "",
	}
}


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
                newNote = Note.Note()
                newNote.contents = n.childNodes[0].nodeValue
                logging.debug("Contents %s" % newNote)
                #this is not a typo, stickynotes puts the date the note was
                #created in the title attribute???
                newNote.modified = n.attributes["title"].nodeValue
                #add to store
                self.notes.append(newNote)
            self.set_status(DataProvider.STATUS_DONE_INIT_OK)
        except:
            logging.warn("Error parsing note file")
            self.set_status(DataProvider.STATUS_DONE_INIT_ERROR)                
            
    def get(self):
        DataProvider.DataProviderBase.get(self)
        for n in self.notes:
            yield n    

class NoteConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,note" : self.text_to_note
                            }
                            
                            
    def text_to_note(self, measure):
        n = Note.Note()
        n.title = "Note Title"
        n.contents = measure
        return n
