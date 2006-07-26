import os
from os.path import abspath, expanduser
import sys
import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Feed as Feed

try:
    import OPML
except:
    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"python-opml-0.5"))
    import OPML

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
    FEED_FILE = "~/.liferea/feedlist.opml"
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Liferea"), _("Sync your liferea feeds"))
        self.icon_name = "liferea"
        self.feedlist = None
        
    def initialize(self):
        self.feedlist = OPML.import_opml(abspath(expanduser(LifereaSource.FEED_FILE)))
        if self.feedlist is None:
            raise Exceptions.InitializeError
        
    def get(self):
        for i in range(0,5):
            feed = Feed.Feed()
            feed.title = i
            yield feed
		
