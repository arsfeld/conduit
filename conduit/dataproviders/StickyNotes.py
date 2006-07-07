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
		"in_type": "file",
		"out_type": "file"
	},
	"StickyNoteSink" : {
		"name": _("StickyNote Sink"),
		"description": _("Sink for synchronizing StickyNotes"),
		"type": "sink",
		"category": "Notes",
		"in_type": "file",
		"out_type": "file"
	}
	
}


class StickyNoteSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("StickyNote Source"), _("Source for synchronizing StickyNotes"))
        self.icon_name = "sticky-notes"

class StickyNoteSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("StickyNote Sink"), _("Sink for synchronizing StickyNotes"))
        self.icon_name = "sticky-notes"
