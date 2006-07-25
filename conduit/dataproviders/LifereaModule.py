import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes.Feed as Feed

MODULES = {
	"LifereaSource" : {
		"name": _("Liferea"),
		"description": _("Sync your liferea feeds"),
		"type": "source",
		"category": "Test",
		"in_type": "feed",
		"out_type": "feed"
	}	
}

class LifereaSource(DataProvider.DataSource):
    FEED_FILE = "~/liferea/feedlist.opml"
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("File Source"), _("Source for synchronizing files"))
        self.icon_name = "liferea"
        
    def get(self):
        for i in range(0,5):
            feed = Feed.Feed()
            feed.title = i
            yield feed
		
