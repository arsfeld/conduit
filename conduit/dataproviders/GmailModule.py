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
	}
}

class GmailBase(DataProvider.DataProviderBase):
    """
    Simple wrapper to share gmail login stuff
    """
    def __init__(self):
        self.username = ""
        self.password = ""
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
            
        def set_tag(param):
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
                    "Name" : "Get Emails Tagged With:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_tag
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
                    logging.debug("GOT %s" % mail)
                    yield mail
        

class GmailEmailSink(GmailBase, DataProvider.DataSink):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSink.__init__(self, _("Gmail Email Sink"), _("Sync your Gmail Emails"))
        self.icon_name = "internet-mail"

        self.label = "Sync"
        self.skipInbox = True
        
    def configure(self, window):
        def set_username(param):
            self.username = param
        
        def set_password(param):
            self.password = param
            
        def set_tag(param):
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
                    "Name" : "Save Emails With Tag:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_tag
                    },                       
                    {
                    "Name" : "Save Emails With Tag:",
                    "Widget" : gtk.CheckButton,
                    "Callback" : set_skip_inbox
                    }                                 
                ]
        
        #We just use a simple configuration dialog
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        #This call blocks
        dialog.run()
        
    def put(self, data):
        DataProvider.DataProviderBase.put(self, data)        
        logging.debug("Putting %s" % data)   

class GmailContactSource(GmailBase, DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Gmail Email Ssource"), _("Sync your Gmail Emails"))
        self.icon_name = "contact-new"

class GmailContactSink(GmailBase, DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("Gmail Email Sink"), _("Sync your Gmail Emails"))
        self.icon_name = "contact-new"
