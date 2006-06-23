from gettext import gettext as _

import DataProvider

MODULES = {
	"GmailSource" : {
		"name": _("Gmail Source"),
		"description": _("Source for synchronizing Gmail Data"),
		"type": "source",
		"in": "file",
		"out": "file"
	},
	"GmailSink" : {
		"name": _("Gmail Sink"),
		"description": _("Sink for synchronizing Gmail Data"),
		"type": "sink",
		"in": "file",
		"out": "file"
	}
	
}

#TODO: Inherit from Source
class GmailSource(DataProvider.DataProviderModel):
	def __init__(self):
		DataProvider.DataProviderModel.__init__(self, _("Gmail Source"), _("Source for synchronizing files"))
		
#TODO: Inherit from Sink		
class GmailSink(DataProvider.DataProviderModel):
	def __init__(self):
		DataProvider.DataProviderModel.__init__(self, _("Gmail Sink"), _("Sink for synchronizing files"))
