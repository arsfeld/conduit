import gtk
import gobject
from gettext import gettext as _

import DataProvider

MODULES = {
	"GmailSource" : {
		"name": _("Gmail Source"),
		"description": _("Source for synchronizing Gmail data"),
		"category": "Test",
		"type": "source",
		"in_type": "file",
		"out_type": "file"
	},
	"GmailSink" : {
		"name": _("Gmail Sink"),
		"description": _("Sink for synchronizing Gmail data"),
		"type": "sink",
		"category": "Test",
		"in_type": "file",
		"out_type": "file"
	}
	
}

#TODO: Inherit from Source
class GmailSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Gmail Source"), _("Source for synchronizing Gmail data"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("applications-internet", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc        
		
#TODO: Inherit from Sink		
class GmailSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("Gmail Sink"), _("Sink for synchronizing Gmail data"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("applications-internet", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc        
