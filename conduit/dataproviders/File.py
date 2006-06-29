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

#TODO: Inherit from Source
class FileSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("File Source"), _("Source for synchronizing files"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("gtk-file", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc

		
#TODO: Inherit from Sink		
class FileSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("File Sink"), _("Sink for synchronizing files"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("gtk-file", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc

