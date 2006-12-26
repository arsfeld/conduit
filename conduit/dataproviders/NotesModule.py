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
	"TomboyNoteSource" :    { "type": "dataprovider" },
	"NoteConverter" :       { "type": "converter"}
}

class TomboyNoteSource(DataProvider.DataSource):

    _name_ = _("Tomboy Source")
    _description = _("Source for synchronizing Tomboy Notes")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    NOTE_DIR = os.path.join(os.path.expanduser("~"),".tomboy")

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self, _("Tomboy Source"))
        self.notes = None
        
    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return os.path.exists(TomboyNoteSource.NOTE_DIR)

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        
        self.notes = []

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
                
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return self.notes[index]
                
    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.notes)

    def finish(self):
        self.notes = None

class NoteConverter:

    _name_ = "Note Data Type"

    def __init__(self):
        self.conversions =  {    
                            "text,note" : self.text_to_note,
                            "note,text" : self.note_to_text,
                            "note,file" : self.note_to_file
                            }
                            
                            
    def text_to_note(self, measure):
        n = Note.Note()
        n.title = "Note Title"
        n.contents = measure
        return n

    def note_to_text(self, note):
        return note.contents

    def note_to_file(self, note):
        f = File.new_from_tempfile(note.contents)
        if len(note.title) > 0:
            f.force_new_filename("%s.%s_note" % (note.title, note.createdUsing))
        else:
            #This is for stickynotes cause the title field is seldom used
            f.force_new_filename("%s.%s_note" % (f.get_filename(), note.createdUsing))
        return f
