import os
import sys
import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes.Email as Email

import email
try:
    import libgmail
except ImportError:
    logging.warn("Note: Using built in libgmail")
    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"libgmail-0.1.4"))
    import libgmail


MODULES = {
	"GmailEmailSource" : {
		"name": _("Gmail Email Source"),
		"description": _("Sync your Gmail Emails"),
		"category": "Gmail",
		"type": "source",
		"in_type": "email",
		"out_type": "email"
	},
	"GmailEmailSink" : {
		"name": _("Gmail Email Sink"),
		"description": _("Sync your Gmail Emails"),
		"type": "sink",
		"category": "Gmail",
		"in_type": "email",
		"out_type": "email"
	},
	"GmailContactSource" : {
		"name": _("Gmail Contacts Source"),
		"description": _("Sync your Gmail Contacts"),
		"type": "source",
		"category": "Gmail",
		"in_type": "vCard",
		"out_type": "vCard"
	},
	"GmailContactSink" : {
		"name": _("Gmail Contacts Sink"),
		"description": _("Sync your Gmail Contacts"),
		"type": "sink",
		"category": "Gmail",
		"in_type": "vCard",
		"out_type": "vCard"
	},
	"EmailSinkConverter" : {
		"name": _("Email Sink Converter"),
		"description": _("I Concur"),
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": "",
	}           
}

class GmailBase(DataProvider.DataProviderBase):
    """
    Simple wrapper to share gmail login stuff
    """
    def __init__(self):
        self.username = ""
        self.password = ""
        self.label = "Sync"

        self.loggedIn = False
        self.ga = None
    
    def initialize(self):
        DataProvider.DataProviderBase.initialize(self)        
        self.ga = libgmail.GmailAccount(self.username, self.password)
        try:
            self.ga.login()
            self.set_status(DataProvider.STATUS_DONE_INIT_OK)             
            self.loggedIn = True
        except:
            logging.info("Gmail Login Failed")
            self.set_status(DataProvider.STATUS_DONE_INIT_ERROR)                      
    

class GmailEmailSource(GmailBase, DataProvider.DataSource):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSource.__init__(self, _("Gmail Email Source"), _("Sync your Gmail Emails"))
        self.icon_name = "internet-mail"
        
    def configure(self, window):
        def set_username(param):
            self.username = param
        
        def set_password(param):
            self.password = param
            
        def set_label(param):
            self.label = param        
        
        #Define the items in the configure dialogue
        items = [
                    {
                    "Name" : "Gmail Username:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_username
                    },
                    {
                    "Name" : "Gmail Password:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_password
                    },
                    {
                    "Name" : "Get Emails Labelged With:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_label
                    }                       
                ]
        
        #We just use a simple configuration dialog
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        #This call blocks
        dialog.run()
        
    def get(self):
        DataProvider.DataProviderBase.get(self)    
        if self.loggedIn:
            result = self.ga.getMessagesByLabel(self.label)
            for thread in result:
                for message in thread:
                    mail = Email.Email()
                    mail.create_from_raw_source(message.source)
                    yield mail
        

class GmailEmailSink(GmailBase, DataProvider.DataSink):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSink.__init__(self, _("Gmail Email Sink"), _("Sync your Gmail Emails"))
        self.icon_name = "internet-mail"
        
        self.skipInbox = True
        
    def configure(self, window):
        def set_username(param):
            self.username = param
        
        def set_password(param):
            self.password = param
            
        def set_label(param):
            self.label = param
            
        def set_skip_inbox(param):
            self.skipInbox = param
        
        #Define the items in the configure dialogue
        items = [
                    {
                    "Name" : "Gmail Username:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_username
                    },
                    {
                    "Name" : "Gmail Password:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_password
                    },
                    {
                    "Name" : "Save Emails With Label:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_label
                    },                       
                    {
                    "Name" : "Skip Inbox?:",
                    "Widget" : gtk.CheckButton,
                    "Callback" : set_skip_inbox
                    }                                 
                ]
        
        #We just use a simple configuration dialog
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        #This call blocks
        dialog.run()
        
    def put(self, email):
        DataProvider.DataProviderBase.put(self, email)        
        
        if email.has_attachments():
            attach = email.attachments
        else:
            attach = None
        
        msg = libgmail.GmailComposedMessage(
                                to="", 
                                subject=email.subject, 
                                body=email.content,
                                filenames=attach)

        draftMsg = self.ga.sendMessage(msg, asDraft = True)

        if draftMsg and self.label:
            try:
                draftMsg.addLabel(self.label)
            except Exception, err:
                import traceback
                traceback.print_exc()
                print err
        
class EmailSinkConverter:
    def __init__(self):
        self.conversions =  {    
                            "file,email" : self.file_to_email,
                            "text,email" : self.text_to_email
                            }
                            
                            
    def file_to_email(self, thefile):
        """
        If the file is non binary then include it as the
        Subject of the message. Otherwise include it as an attachment
        return str(measure) + " was text now a note"        
        """
        NON_BINARY_MIMETYPES = [
                "text/plain",
                "text/html"
                ]
        
        if thefile.get_mimetype() in NON_BINARY_MIMETYPES:
            #insert the contents into the email
            logging.debug("Inserting file contents into email")
            email = Email.Email()
            email.create(   "",                             #to
                            "",                             #from
                            thefile.get_filename(),         #subject
                            thefile.get_contents_as_text()  #contents
                            )
            return email
        else:
            #binary file so send as attachment
            logging.debug("Binary file, attaching to email")
            email = Email.Email()
            email.create(   "",                             #to
                            "",                             #from
                            thefile.get_filename(),         #subject
                            "Attached"                      #contents
                            )
            email.add_attachment(thefile.create_local_tempfile())
            return email
            
    def text_to_email(self, text):
        email = Email.Email()
        email.create(   "",                             #to
                        "",                             #from
                        "",                             #subject
                        text                            #contents
                        )
        return email
        

class GmailContactSource(GmailBase, DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Gmail Email Ssource"), _("Sync your Gmail Emails"))
        self.icon_name = "contact-new"

class GmailContactSink(GmailBase, DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("Gmail Email Sink"), _("Sync your Gmail Emails"))
        self.icon_name = "contact-new"
