from gettext import gettext as _

import DataProvider

MODULES = {
	"GmailSource" : {
		"name": _("Gmail Source"),
		"description": _("Source for synchronizing Gmail Data"),
		"category": "Test",
		"type": "source",
		"in": "file",
		"out": "file"
	},
	"GmailSink" : {
		"name": _("Gmail Sink"),
		"description": _("Sink for synchronizing Gmail Data"),
		"type": "sink",
		"category": "Test",
		"in": "file",
		"out": "file"
	}
	
}

#TODO: Inherit from Source
class GmailSource(DataProvider.DataSource):
	def __init__(self):
		DataProvider.DataSource.__init__(self, _("Gmail Source"), _("Source for synchronizing files"))
		
#TODO: Inherit from Sink		
class GmailSink(DataProvider.DataSink):
	def __init__(self):
		DataProvider.DataSink.__init__(self, _("Gmail Sink"), _("Sink for synchronizing files"))
