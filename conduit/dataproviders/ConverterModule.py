
import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils

import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Text as Text
import conduit.datatypes.Email as Email

MODULES = {
        "EmailConverter" :      { "type": "converter" },
        "NoteConverter" :       { "type": "converter" },
        "ContactConverter" :    { "type": "converter" },
        "EventConverter" :      { "type": "converter" },
        "FileConverter" :       { "type": "converter" },
        "TaggedFileConverter" : { "type": "converter" }
}

class EmailConverter:
    def __init__(self):
        self.conversions =  {    
                            "email,text"    : self.email_to_text,
                            "file,email"    : self.file_to_email,
                            "text,email"    : self.text_to_email
                            }
                            
                            
    def email_to_text(self, email):
        t = Text.Text(
                    text=email.get_email_string()
                    )
        return Utils.retain_info_in_conversion(email, t)

    def file_to_email(self, thefile):
        """
        If the file is non binary then include it as the
        Subject of the message. Otherwise include it as an attachment
        """
        mimeCategory = thefile.get_mimetype().split('/')[0]
        if mimeCategory == "text":
            #insert the contents into the email
            logd("Inserting file contents into email")
            email = Email.Email(
                            None,
                            subject=thefile.get_filename(),
                            content=thefile.get_contents_as_text()
                            )
        else:
            #binary file so send as attachment
            logd("Binary file, attaching to email")
            email = Email.Email(
                            None,
                            subject=thefile.get_filename(),
                            content="Attached"
                            )
            email.add_attachment(thefile.get_local_uri())

        return Utils.retain_info_in_conversion(thefile, email)
            
    def text_to_email(self, text):
        email = Email.Email(
                        None,
                        content=text.get_string()
                        )
        return Utils.retain_info_in_conversion(text, email)


class NoteConverter:
    def __init__(self):
        self.conversions =  {  
                            "text,note"     : self.text_to_note,  
                            "note,text"     : self.note_to_text,
                            "note,file"     : self.note_to_file
                            }

    def text_to_note(self, text):
        n = Note.Note(
                    title="Note-"+Utils.random_string(),
                    contents=text
                    )
        return n
                            
    def note_to_text(self, note):
        t = Text.Text(
                    text=note.get_note_string()
                    )
        return Utils.retain_info_in_conversion(note, t)

    def note_to_file(self, note):
        f = Utils.new_tempfile(note.contents)
        return Utils.retain_info_in_conversion(note, f)

class ContactConverter:
    def __init__(self):
        self.conversions =  {    
                            "contact,file"    : self.contact_to_file,
                            "contact,text"    : self.contact_to_text,
                            "file,contact"    : self.file_to_contact,
                            }
                            
    def contact_to_file(self, contact):
        #get vcard data
        f = Utils.new_tempfile(contact.get_vcard_string())
        return Utils.retain_info_in_conversion(contact, t)

    def contact_to_text(self, contact):
        #get vcard data
        t = Text.Text(
                    text=contact.get_vcard_string()
                    )
        return Utils.retain_info_in_conversion(contact, t)

    def file_to_contact(self, f):
        c = Contact.Contact(None)
        c.readVCard(f.get_contents_as_text())
        return Utils.retain_info_in_conversion(f, c)

class EventConverter:
    def __init__(self):
        self.conversions =  {    
                            "event,file"    : self.event_to_file,
                            "event,text"    : self.event_to_text,
                            "file,event"    : self.file_to_event,
                            "text,event"    : self.text_to_event,
                            }
                            
    def event_to_file(self, event):
        #get ical data
        f = Utils.new_tempfile(event.get_ical_string())
        return Utils.retain_info_in_conversion(event, f)

    def event_to_text(self, event):
        t = Text.Text(
                    text=event.get_ical_string()
                    )
        return Utils.retain_info_in_conversion(event, t)

    def file_to_event(self, f):
        e = Event.Event(None)
        e.set_from_ical_string(f.get_contents_as_text())
        return Utils.retain_info_in_conversion(f, e)

    def text_to_event(self, text):
        e = Event.Event(None)
        e.set_from_ical_string(text.get_string())
        return Utils.retain_info_in_conversion(text, e)

class FileConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,file" : self.text_to_file,
                            "file,text" : self.file_to_text
                            }
        
    def text_to_file(self, theText):
        return Utils.new_tempfile(str(theText))

    def file_to_text(self, theFile):
        mime = theFile.get_mimetype()
        try:
            #check its a text type
            mime.index("text")
            raw = theFile.get_contents_as_text()
            text = Text.Text(text=raw)
            return Utils.retain_info_in_conversion(theFile, text)
        except ValueError:
            raise Exception(
                    "Could not convert %s to text. Binary file" % 
                    theFile._get_text_uri()
                    )
       

class TaggedFileConverter:
    def __init__(self):
        self.conversions =  {    
                            "taggedfile,file" : self.taggedfile_to_file,
                            "file,taggedfile" : self.file_to_taggedfile
                            }            
    def taggedfile_to_file(self, thefile):
        return thefile

    def file_to_taggedfile(self, thefile):
        #FIXME: implent this
        return thefile

