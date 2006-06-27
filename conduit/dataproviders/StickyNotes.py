import gtk
import gobject
from gettext import gettext as _

import conduit
import conduit.DataProvider as DataProvider

MODULES = {
	"StickyNoteSource" : {
		"name": _("StickyNote Source"),
		"description": _("Source for synchronizing StickyNotes"),
		"type": "source",
		"category": "Notes",
		"in": "file",
		"out": "file"
	},
	"StickyNoteSink" : {
		"name": _("StickyNote Sink"),
		"description": _("Sink for synchronizing StickyNotes"),
		"type": "sink",
		"category": "Notes",
		"in": "file",
		"out": "file"
	}
	
}

#TODO: Inherit from Source
class StickyNoteSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("StickyNote Source"), _("Source for synchronizing StickyNotes"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("gtk-justify-fill", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc

#TODO: Inherit from Sink		
class StickyNoteSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("StickyNote Sink"), _("Sink for synchronizing StickyNotes"))
        try:
            self.icon = gtk.icon_theme_get_default().load_icon("gtk-justify-fill", 16, 0)
        except gobject.GError, exc:
            self.icon = None
            print >> stderr, "can't load icon", exc        
