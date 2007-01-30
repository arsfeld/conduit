import os
from os.path import abspath, expanduser
import sys
import gtk
from gettext import gettext as _


import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Feed as Feed
import conduit.Utils as Utils

Utils.dataprovider_add_dir_to_path(__file__, "python-opml-0.5")
import OPML

MODULES = {
	"LifereaSource" : { "type": "dataprovider" }	
}

class LifereaSource(DataProvider.DataSource):

    _name_ = _("Liferea Feeds")
    _description_ = _("Sync your liferea RSS feeds")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "feed"
    _out_type_ = "feed"
    _icon_ = "liferea"

    FEED_FILE = "~/.liferea/feedlist.opml"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
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
