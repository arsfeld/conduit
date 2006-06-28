import gtk
import gobject
from gettext import gettext as _

import conduit
import conduit.DataProvider as DataProvider

MODULES = {
	"EvoEmailSource" : {
		"name": _("EvoEmail Source"),
		"description": _("Source for synchronizing Evolution Emails"),
		"type": "source",
		"category": "Notes",
		"in": "file",
		"out": "file"
	},
	"EvoEmailSink" : {
		"name": _("EvoEmail Sink"),
		"description": _("Sink for synchronizing Evolution Emails"),
		"type": "sink",
		"category": "Notes",
		"in": "file",
		"out": "file"
	},
	"EvoCalSource" : {
		"name": _("EvoCal Source"),
		"description": _("Source for synchronizing Evolution Calendar Data"),
		"type": "source",
		"category": "Notes",
		"in": "file",
		"out": "file"
	},
	"EvoCalSink" : {
		"name": _("EvoCal Sink"),
		"description": _("Sink for synchronizing Evolution Calendar Data"),
		"type": "sink",
		"category": "Notes",
		"in": "file",
		"out": "file"
	}	
	
}

class EvoEmailSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("EvoEmail Source"), _("Source for synchronizing Evolution Emails"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("internet-mail", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc

class EvoEmailSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("EvoEmail Sink"), _("Sink for synchronizing Evolution Emails"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("internet-mail", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc
            
class EvoCalSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("EvoCal Source"), _("Source for synchronizing Evolution Calendar data"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("stock_calendar", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc

class EvoCalSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("EvoCal Sink"), _("Sink for synchronizing Evolution Calendar data"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("stock_calendar", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc              
