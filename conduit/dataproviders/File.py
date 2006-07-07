import gtk
import gobject
from gettext import gettext as _

import DataProvider

MODULES = {
	"FileSource" : {
		"name": _("File Source"),
		"description": _("Source for synchronizing files"),
		"type": "source",
		"category": "Local",
		"in_type": "file",
		"out_type": "file"
	},
	"FileSink" : {
		"name": _("File Sink"),
		"description": _("Sink for synchronizing files"),
		"type": "sink",
		"category": "Local",
		"in_type": "file",
		"out_type": "file"
	}
	
}

class FileSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("File Source"), _("Source for synchronizing files"))
        self.icon_name = "gtk-file"
		
class FileSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("File Sink"), _("Sink for synchronizing files"))
        self.icon_name = "gtk-file"
