import re
import logging
log = logging.getLogger("modules.Converter")

import conduit
import conduit.Utils as Utils
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Text as Text
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.datatypes.Note as Note
import conduit.datatypes.Setting as Setting

MODULES = {
        "EmailConverter" :      { "type": "converter" },
        "NoteConverter" :       { "type": "converter" },
        "ContactConverter" :    { "type": "converter" },
        "EventConverter" :      { "type": "converter" },
        "FileConverter" :       { "type": "converter" },
        "SettingConverter" :    { "type": "converter" }
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
                        content=text.get_string()
                        )
        return email

    def email_to_file(self, email, **kwargs):
        f = File.TempFile(email.get_email_string())
        return f        

    def file_to_email(self, thefile, **kwargs):
        """
        If the file is non binary then include it as the
        Subject of the message. Otherwise include it as an attachment
        """
        mimeCategory = thefile.get_mimetype().split('/')[0]
        if mimeCategory == "text":
            #insert the contents into the email
            log.debug("Inserting file contents into email")
            email = Email.Email(
                            subject=thefile.get_filename(),
                            content=thefile.get_contents_as_text()
                            )
        else:
            #binary file so send as attachment
            log.debug("Binary file, attaching to email")
            email = Email.Email(
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
        f = File.TempFile(note.get_contents())
        f.force_new_filename(note.get_title())
        f.force_new_file_extension(".txt")
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
        c = Contact.Contact()
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
        e = Event.Event()
        e.set_from_ical_string(f.get_contents_as_text())
        return e

    def text_to_event(self, text, **kwargs):
        e = Event.Event()
        e.set_from_ical_string(text.get_string())
        return e

class FileConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,file" : self.text_to_file,
                            "file,text" : self.file_to_text,
                            "file,note" : self.file_to_note
                            }
        
    def text_to_file(self, text, **kwargs):
        return Utils.new_tempfile(text.get_string())

    def file_to_text(self, f, **kwargs):
        test = None
        if f.get_mimetype().startswith("text"):
            text = Text.Text(
                            text=f.get_contents_as_text()
                            )
        return text

    def file_to_note(self, f, **kwargs):
        note = None
        if f.get_mimetype().startswith("text"):
            title,ext = f.get_filename_and_extension()
            #remove the file extension....
            note = Note.Note(
                    title=title,
                    contents=f.get_contents_as_text()
                    )
        return note
       
class SettingConverter(object):
    def __init__(self):
        self.conversions =  {    
                            "setting,text"    : self.setting_to_text,
                            "setting,file"    : self.setting_to_file,
                            "text,setting"    : self.text_to_setting,
                            "file,setting"    : self.file_to_setting
                            }
        #recognizes key value in text strings
        self.regex = re.compile(r"^key:(.+)\nvalue:(.*)$")
                            
    def _to_text(self, setting):
        return "key:%s\nvalue:%s" % (setting.key, setting.value)
        
    def _to_key_value(self, txt):
        m = self.regex.match(txt)
        if m != None and len(m.groups()) == 2:
            return m.group(1),m.group(2)
        else:
            return None,None
            
    def setting_to_text(self, setting):
        t = Text.Text(
                    text=self._to_text(setting)
                    )
        return t
        
    def text_to_setting(self, text):
        setting = None
        k,v = self._to_key_value(text.get_string())
        if k != None and v != None:
            setting = Setting.Setting(
                                key=k,
                                value=v
                                )
        return setting
        
    def setting_to_file(self, setting):
        f = File.TempFile(
                        self._to_text(setting)
                        )
        f.force_new_filename(setting.key.replace("/","_"))
        f.force_new_file_extension(".txt")
        return f
        
    def file_to_setting(self, f):
        setting = None
        if f.get_mimetype().startswith("text"):
            txt = f.get_contents_as_text()
            k,v = self._to_key_value(txt)
            if k != None and v != None:
                setting = Setting.Setting(
                                    key=k,
                                    value=v
                                    )
        return setting

            
            
        
        
        
     
