import gtk
import gobject
from gettext import gettext as _

import logging
import conduit
import DataProvider

MODULES = {
	"GmailSource" : {
		"name": _("Gmail Source"),
		"description": _("Source for synchronizing Gmail data"),
		"category": "Test",
		"type": "source",
		"in_type": "text",
		"out_type": "text"
	},
	"GmailSink" : {
		"name": _("Gmail Sink"),
		"description": _("Sink for synchronizing Gmail data"),
		"type": "sink",
		"category": "Test",
		"in_type": "text",
		"out_type": "text"
	}
	
}

class GmailSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Gmail Source"), _("Source for synchronizing Gmail data"))
        self.icon_name = "applications-internet"
        
        #gmail specific settings
        self.username = None
        self.password = None
        self.tag = "Sync"
        
    def configure(self, window):
        def set_username(param):
            self.username = param
        
        def set_password(param):
            self.password = param
            
        def set_tag(param):
            self.tag = param        
        
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
        
class GmailSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("Gmail Sink"), _("Sink for synchronizing Gmail data"))
        self.icon_name = "applications-internet"

        #gmail specific settings
        self.username = None
        self.password = None
        self.tag = "Sync"
        self.skipInbox = True
        
    def configure(self, window):
        def set_username(param):
            self.username = param
        
        def set_password(param):
            self.password = param
            
        def set_tag(param):
            self.tag = param
            
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
