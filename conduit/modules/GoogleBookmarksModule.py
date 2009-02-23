# Copyright 2009 - Andrew Stomont <andyjstormont@googlemail.com>
import urllib2
import xml.dom.minidom
import logging
log = logging.getLogger("modules.GoogleBookmarks")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Bookmark as Bookmark

MODULES = {
    "GoogleBookmarksDataProviderSource" : { "type": "dataprovider" }
}

class GoogleBookmarksDataProviderSource(DataProvider.DataSource):

    _name_ = "Google Bookmarks"
    _description_ = "Sync your Google Bookmarks"
    _category_ = conduit.dataproviders.CATEGORY_BOOKMARKS
    _module_type_ = "source"
    _out_type_ = "bookmark"
    _icon_ = "applications-internet"
    _configurable_ = True

    def __init__(self):
        DataProvider.DataSource.__init__(self)
        self.update_configuration(
            username = "",
            password = ""
        )
        self._bookmarks = []

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self._bookmarks = []
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password('Google Search History', 'www.google.com', self.username, self.password)
        opener = urllib2.build_opener(auth_handler)
        bookmark_feed = opener.open("https://www.google.com/bookmarks/?output=rss")
        for item in xml.dom.minidom.parse(bookmark_feed).documentElement.getElementsByTagName("item"):
            title = item.getElementsByTagName("title")[0].childNodes[0].data
            link = item.getElementsByTagName("link")[0].childNodes[0].data
            bookmark = Bookmark.Bookmark(title, link)
            bookmark.set_UID(bookmark.get_hash())
            self._bookmarks.append(bookmark)

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        retval = []
        for bookmark in self._bookmarks:
            retval.append(bookmark.get_UID())
        return retval
        
    def get(self, luid):
        DataProvider.DataSource.get(self, luid)
        for bookmark in self._bookmarks:
            if bookmark.get_UID() == luid:
                return bookmark

    def get_UID(self):
        return self.username

    def config_setup(self, config):
        config.add_section("Login Details")
        config.add_item("Username", "text",
            config_name = "username",
        )
        config.add_item("Password", "text",
            config_name = "password",
            password = True
        )

