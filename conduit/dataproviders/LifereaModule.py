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
		"category": DataProvider.CATEGORY_LOCAL,
		"in_type": "feed",
		"out_type": "feed",
                "icon": "liferea"
	}	
}

class LifereaSource(DataProvider.DataSource):
    FEED_FILE = "~/.liferea/feedlist.opml"
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Liferea"), _("Sync your liferea feeds"), "liferea")
        self.feedlist = None
        
    def initialize(self):
        """
        Load Liferea Source if feed exists
        """
        return os.path.exists(LifereaSource.FEED_FILE)
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.feedlist = OPML.import_opml(abspath(expanduser(LifereaSource.FEED_FILE)))
        if self.feedlist is None:
            raise Exceptions.RefreshError
    
    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return 5

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        feed = Feed.Feed()
        feed.title = index
        return feed

    def finish(self):
        self.feedlist = None
