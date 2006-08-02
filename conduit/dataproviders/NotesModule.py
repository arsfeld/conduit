import gtk
from gettext import gettext as _
from xml.dom import minidom

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File

import os
import os.path


MODULES = {
	"TomboyNoteSource" : {
		"name": _("Tomboy Source"),
		"description": _("Source for synchronizing Tomboy Notes"),
		"type": "source",
		"category": "Notes",
		"in_type": "note",
		"out_type": "note"
	},
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

class TomboyNoteSource(DataProvider.DataSource):
    NOTE_DIR = os.path.join(os.path.expanduser("~"),".tomboy")
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Tomboy Source"), _("Source for synchronizing Tomboy Notes"))
        self.icon_name = "tomboy"
        self.notes = []
        
    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return os.path.exists(TomboyNoteSource.NOTE_DIR)

    def refresh(self):
        files = [i for i in os.listdir(TomboyNoteSource.NOTE_DIR) if i[-5:] == ".note"]

        #Parse the files into notes        
        for f in files:
            xml = minidom.parse(os.path.join(TomboyNoteSource.NOTE_DIR,f))
            try:
                #Convenience wrapper to overcome my dumbness, minidoms verboseness
                #and my lazyness
                def i_hate_xml(verbose):
                    return verbose[0].childNodes[0].data
                    
                title = i_hate_xml(xml.documentElement.getElementsByTagName("title"))
                modified = i_hate_xml(xml.documentElement.getElementsByTagName("last-change-date"))
                content = i_hate_xml(xml.documentElement.getElementsByTagName("note-content"))

                #logging.debug("Title: %s, Modified: %s \nContent:\n%s" % (title, modified, content))
                note = Note.Note(title, modified, content)
                note.createdUsing = "tomboy"
                self.notes.append(note)
            except:
                logging.warn("Error parsing note file")
                raise Exceptions.RefreshError
                
    def get(self):
        for n in self.notes:
            yield n    
                

class StickyNoteSource(DataProvider.DataSource):
    NOTE_FILE = os.path.join(os.path.expanduser("~"),".gnome2","stickynotes_applet")
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("StickyNote Source"), _("Source for synchronizing StickyNotes"))
        self.icon_name = "sticky-notes"
        
        self.xml = None
        self.notes = []
        
    def initialize(self):
        """
        Loads the stickynotes source if the user has used stickynotes before
        """
        return os.path.exists(StickyNoteSource.NOTE_FILE)        
        
    def refresh(self):
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
                newNote.createdUsing = "stickynotes"
                #add to store
                self.notes.append(newNote)
        except:
            logging.warn("Error parsing note file")
            raise Exceptions.RefreshError            
            
    def get(self):
        for n in self.notes:
            yield n    

class NoteConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,note" : self.text_to_note,
                            "note,file" : self.note_to_file
                            }
                            
                            
    def text_to_note(self, measure):
        n = Note.Note()
        n.title = "Note Title"
        n.contents = measure
        return n

    def note_to_file(self, note):
        f = File.new_from_tempfile(note.contents)
        if len(note.title) > 0:
            f.force_new_filename("%s.%s_note" % (note.title, note.createdUsing))
        else:
            #FIXME: This is for stickynotes cause the title field is seldom used
            f.force_new_filename("%s.%s_note" % (f.get_filename(), note.createdUsing))
        return f
