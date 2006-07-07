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
		"in_type": "file",
		"out_type": "file"
	},
	"EvoEmailSink" : {
		"name": _("EvoEmail Sink"),
		"description": _("Sink for synchronizing Evolution Emails"),
		"type": "sink",
		"category": "Notes",
		"in_type": "file",
		"out_type": "file"
	},
	"EvoCalSource" : {
		"name": _("EvoCal Source"),
		"description": _("Source for synchronizing Evolution Calendar Data"),
		"type": "source",
		"category": "Notes",
		"in_type": "file",
		"out_type": "file"
	},
	"EvoCalSink" : {
		"name": _("EvoCal Sink"),
		"description": _("Sink for synchronizing Evolution Calendar Data"),
		"type": "sink",
		"category": "Notes",
		"in_type": "file",
		"out_type": "file"
	}	
	
}

class EvoEmailSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("EvoEmail Source"), _("Source for synchronizing Evolution Emails"))
        self.icon_name = "internet-mail"

class EvoEmailSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("EvoEmail Sink"), _("Sink for synchronizing Evolution Emails"))
        self.icon_name = "internet-mail"
            
class EvoCalSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("EvoCal Source"), _("Source for synchronizing Evolution Calendar data"))
        self.icon_name = "stock_calendar"

class EvoCalSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("EvoCal Sink"), _("Sink for synchronizing Evolution Calendar data"))
        self.icon_name = "stock_calendar"
