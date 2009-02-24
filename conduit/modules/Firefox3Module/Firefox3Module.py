# Copyright 2009 - Andrew Stormont <andyjstormont@googlemail.com>

import os.path
import ConfigParser
import sqlite3
import logging
log = logging.getLogger("modules.Firefox3")

from gettext import gettext as _

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
import conduit.datatypes.Bookmark as Bookmark
import conduit.Exceptions as Exceptions

MODULES = {
    "Firefox3DataProviderSource" : { "type" : "dataprovider" },
}

class Firefox3DataProviderSource(DataProvider.DataSource):
    """ 
    Firefox 3 Bookmarks datasource
    """

    _name_ = _("Firefox 3 Bookmarks")
    _description_ = _("Syncronize your Firefox 3 Bookmarks")
    _category_ = conduit.dataproviders.CATEGORY_BOOKMARKS
    _module_type_ = "source"
    _out_type_ = "bookmark"
    _icon_ = "applications-internet"
    _configurable_ = True

    BOOKMARKS_ROOT, BOOKMARKS_MENU, BOOKMARKS_TOOLBAR = range(1,4)

    def __init__(self):
        DataProvider.DataSource.__init__(self)

        self._bookmarks = []
        self._ffdir = os.path.expanduser(os.path.join("~",".mozilla","firefox"))
        self._cf = ConfigParser.ConfigParser()
        self._cf.read(os.path.join(self._ffdir,"profiles.ini"))

        self.update_configuration(
            profilepath = self._cf.get("Profile0", "Path") # default
        )

    def _get_profiles(self):
        retval = []
        for section in self._cf.sections():
            if section != "General":
                retval.append((self._cf.get(section, "Name"), self._cf.get(section, "Path")))
        return retval

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        # sqlite3 is not thread safe, so we cannot preserve connections in this class
        con = sqlite3.connect(os.path.join(self._ffdir,self.profilepath,"places.sqlite"))
        try:
            # table structure
            # moz_bookmarks: id|type|fk|parent|position|title|keyword_id|folder_type|dateAdded|lastModified
            # moz_places: id|url|title|rev_host|visit_count|hidden|typed|favicon_id|frecency
            cur = con.execute("SELECT b.title,p.url FROM moz_bookmarks b, moz_places p WHERE b.fk=p.id;")
        except:
            con.close()
            raise Exceptions.SyncronizeError("Can't read Firefox 3 Bookmarks - Make sure Firefox is closed.")
        for (title, url) in cur.fetchall():
            bookmark = Bookmark.Bookmark(title, url)
            bookmark.set_UID(bookmark.get_hash())
            self._bookmarks.append(bookmark)
        con.close()  

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

    def config_setup(self, config):
        config.add_item(_("Firefox Profile"), "combo",
            config_name = "profilepath",
            choices = [(path, name) for name, path in self._get_profiles()]
        )

    def get_UID(self):
        return Utils.get_user_string()
            
