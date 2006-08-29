import gtk
from gettext import gettext as _
from elementtree import ElementTree

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File

import os
import os.path
import traceback

MODULES = {
	"TomboyNoteSource" : {
		"name": _("Tomboy Source"),
		"description": _("Source for synchronizing Tomboy Notes"),
		"type": "source",
		"category": DataProvider.CATEGORY_LOCAL,
		"in_type": "note",
		"out_type": "note"
	},
	"StickyNoteSource" : {
		"name": _("StickyNote Source"),
		"description": _("Source for synchronizing StickyNotes"),
		"type": "source",
		"category": DataProvider.CATEGORY_LOCAL,
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
        #FIXME: How can I do this namespace bit in ElementTree
        def remove_namespace(string):
            return string.split("}")[1]
        
        #Parse the files into notes
        files = [i for i in os.listdir(TomboyNoteSource.NOTE_DIR) if i[-5:] == ".note"]    
        for f in files:
            try:
                doc = ElementTree.parse(os.path.join(TomboyNoteSource.NOTE_DIR,f)).getroot()
                for i in doc:
                    tag = remove_namespace(i.tag)
                    if tag == "text":
                        for j in i.getchildren():
                            if remove_namespace(j.tag) == "note-content":
                                content = j.text
                    if tag == "last-change-date":
                        modified = i.text
                    if tag == "title":
                        title = i.text            
                            
                #logging.debug("Title: %s, Modified: %s \nContent:\n%s" % (title, modified, content))
                note = Note.Note(str(title), str(modified), str(content))
                note.createdUsing = "tomboy"
                self.notes.append(note)
            except:
                logging.warn("Error parsing note file\n%s" % traceback.format_exc())
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
        try:
            if self.xml is None:
                self.xml = ElementTree.parse(StickyNoteSource.NOTE_FILE).getroot()
            
            for n in self.xml:
                #I think the following is always true... I am mediocre at XML
                if n.tag == "note":
                    newNote = Note.Note()
                    newNote.contents = str(n.text)
                    #this is not a typo, stickynotes puts the date the note was
                    #created in the title attribute???
                    newNote.modified = str(n.get("title"))
                    newNote.createdUsing = "stickynotes"
                    #Use the first line of the note as its title
                    try:
                        newNote.title = str(newNote.contents.split("\n")[0])
                    except:
                        newNote.title = ""
                    #add to store
                    self.notes.append(newNote)
        except:
            logging.warn("Error parsing note file\n%s" % traceback.format_exc())
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
            #This is for stickynotes cause the title field is seldom used
            f.force_new_filename("%s.%s_note" % (f.get_filename(), note.createdUsing))
        return f
