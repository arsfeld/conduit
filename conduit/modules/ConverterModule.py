
import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils

import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Text as Text
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.datatypes.Note as Note

MODULES = {
        "EmailConverter" :      { "type": "converter" },
        "NoteConverter" :       { "type": "converter" },
        "ContactConverter" :    { "type": "converter" },
        "EventConverter" :      { "type": "converter" },
        "FileConverter" :       { "type": "converter" }
}

class EmailConverter:
    def __init__(self):
        self.conversions =  {    
                            "email,text"    : self.email_to_text,
                            "text,email"    : self.text_to_email,
                            "email,file"    : self.email_to_file,
                            "file,email"    : self.file_to_email,
                            }
                            
                            
    def email_to_text(self, email, **kwargs):
        t = Text.Text(
                    text=email.get_email_string()
                    )
        return t

    def text_to_email(self, text, **kwargs):
        email = Email.Email(
                        None,
                        content=text.get_string()
                        )
        return email

    def email_to_file(self, email, **kwargs):
        f = File.TempFile(email.raw)
        return f        

    def file_to_email(self, thefile, **kwargs):
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

        return email


class NoteConverter:
    def __init__(self):
        self.conversions =  {  
                            "text,note"     : self.text_to_note,  
                            "note,text"     : self.note_to_text,
                            "note,file"     : self.note_to_file
                            }

    def text_to_note(self, text, **kwargs):
        n = Note.Note(
                    title="Note-"+Utils.random_string(),
                    contents=text
                    )
        return n
                            
    def note_to_text(self, note, **kwargs):
        t = Text.Text(
                    text=note.get_note_string()
                    )
        return t

    def note_to_file(self, note, **kwargs):
        f = File.TempFile(note.raw)
        f.force_new_filename(note.title)
        return f

class ContactConverter:
    def __init__(self):
        self.conversions =  {
                            "contact,file"    : self.contact_to_file,
                            "contact,text"    : self.contact_to_text,
                            "file,contact"    : self.file_to_contact,
                            }
                            
    def contact_to_file(self, contact, **kwargs):
        #get vcard data
        f = Utils.new_tempfile(contact.get_vcard_string())
        return f

    def contact_to_text(self, contact, **kwargs):
        #get vcard data
        t = Text.Text(
                    text=contact.get_vcard_string()
                    )
        return t

    def file_to_contact(self, f, **kwargs):
        c = Contact.Contact(None)
        c. set_from_vcard_string(f.get_contents_as_text())
        return c

class EventConverter:
    def __init__(self):
        self.conversions =  {    
                            "event,file"    : self.event_to_file,
                            "event,text"    : self.event_to_text,
                            "file,event"    : self.file_to_event,
                            "text,event"    : self.text_to_event,
                            }
                            
    def event_to_file(self, event, **kwargs):
        #get ical data
        f = Utils.new_tempfile(event.get_ical_string())
        return f

    def event_to_text(self, event, **kwargs):
        t = Text.Text(
                    text=event.get_ical_string()
                    )
        return t

    def file_to_event(self, f, **kwargs):
        e = Event.Event(None)
        e.set_from_ical_string(f.get_contents_as_text())
        return e

    def text_to_event(self, text, **kwargs):
        e = Event.Event(None)
        e.set_from_ical_string(text.get_string())
        return e

class FileConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,file" : self.text_to_file,
                            "file,text" : self.file_to_text,
                            "file,note" : self.file_to_note
                            }
        
    def text_to_file(self, theText, **kwargs):
        return Utils.new_tempfile(str(theText))

    def file_to_text(self, theFile, **kwargs):
        mime = theFile.get_mimetype()
        try:
            #check its a text type
            mime.index("text")
            raw = theFile.get_contents_as_text()
            text = Text.Text(text=raw)
            return text
        except ValueError:
            raise Exception(
                    "Could not convert %s to text. Binary file" % 
                    theFile._get_text_uri()
                    )

    def file_to_note(self, theFile, **kwargs):
        mime = theFile.get_mimetype()
        try:
            #check its a text type
            mime.index("text")
            raw = theFile.get_contents_as_text()
            title = theFile.get_filename()
            note = Note.Note(
                    title=title,
                    raw=raw
                    )
            return note
        except ValueError:
            raise Exception(
                    "Could not convert %s to text. Binary file" % 
                    theFile._get_text_uri()
                    )
       
