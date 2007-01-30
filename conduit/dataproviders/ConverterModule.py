
import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils

import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event

MODULES = {
        "TextConverter" :       { "type": "converter" },
        "ContactConverter" :    { "type": "converter" },
        "EventConverter" :      { "type": "converter" },
        "TaggedFileConverter" : { "type": "converter" }
}

class TextConverter:
    def __init__(self):
        self.conversions =  {    
                            "email,text"    : self.to_text,
                            "note,text"     : self.to_text
                            }
                            
                            
    def to_text(self, measure):
        """
        Cheat and hope that modules define __str__()
        """
        if hasattr(measure, "__str__"):
            return str(measure)
        logw("%s does not define __str__()" % measure)
        return ""

class ContactConverter:
    def __init__(self):
        self.conversions =  {    
                            "contact,file"    : self.contact_to_file,
                            "contact,text"    : self.contact_to_text,
                            "file,contact"    : self.file_to_contact,
                            }
                            
    def contact_to_file(self, contact):
        #FIXME: Save contact as a VCard
        return Utils.new_tempfile(str(contact))

    def contact_to_text(self, contact):
        return str(contact)

    def file_to_contact(self, f):
        c = Contact.Contact()
        c.readVCard(f.get_contents_as_text())
        return c

class EventConverter:
    def __init__(self):
        self.conversions =  {    
                            "event,file"    : self.event_to_file,
                            "event,text"    : self.event_to_text,
                            "file,event"    : self.file_to_event,
                            "text,event"    : self.text_to_event,
                            }
                            
    def event_to_file(self, event):
        return Utils.new_tempfile(event.to_string())

    def event_to_text(self, event):
        return event.to_string()

    def file_to_event(self, f):
        e = Event.Event()
        e.read_string(f.get_contents_as_text())
        return e

    def text_to_event(self, text):
        e = Event.Event()
        e.read_string(text)
        return e

class TaggedFileConverter:
    def __init__(self):
        self.conversions =  {    
                            "taggedfile,file" : self.taggedfile_to_file,
                            "file,taggedfile" : self.file_to_taggedfile
                            }            
    def taggedfile_to_file(self, thefile):
        #taggedfile is parent class of file so no conversion neccessary
        return thefile

    def file_to_taggedfile(self, thefile):
        #FIXME: Save URI and kwargs and then chain this on to the new type
        #This means all datatypes must have the same prototype
        #DataType(uri, **kwargs)
        return thefile

