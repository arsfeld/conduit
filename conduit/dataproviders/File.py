from gettext import gettext as _

import DataProvider
#from deskbar.DeskbarHistory import get_deskbar_history

DATAPROVIDERS = {
	"FileSource" : {
		"name": _("File Source"),
		"description": _("Source for synchronizing files"),
		"type": "source",
		"in": "file",
		"out": "file"
	},
	"FileSink" : {
		"name": _("File Sink"),
		"description": _("Sink for synchronizing files"),
		"type": "sink",
		"in": "file",
		"out": "file"
	}
	
}

#TODO: Inherit from Source
class FileSource(DataProvider.DataProviderModel):
	def __init__(self):
		DataProvider.DataProviderModel.__init__(self, _("File Source"), _("Source for synchronizing files"))
		
#TODO: Inherit from Sink		
class FileSink(DataProvider.DataProviderModel):
	def __init__(self):
		DataProvider.DataProviderModel.__init__(self, _("File Sink"), _("Sink for synchronizing files"))
