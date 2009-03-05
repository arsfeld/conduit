# Copyright 2009 - Andrew Stomont <andyjstormont@googlemail.com>
import os
import logging
log = logging.getLogger("modules.NautilusBookmarks")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
import conduit.datatypes.Bookmark as Bookmark

MODULES = {
    "NautilusBookmarksDataProviderTwoWay" : { "type": "dataprovider" }
}

class NautilusBookmarksDataProviderTwoWay(DataProvider.TwoWay):

    _name_ = "Nautilus Bookmarks"
    _description_ = "Sync your Nautilus Bookmarks"
    _category_ = conduit.dataproviders.CATEGORY_BOOKMARKS
    _module_type_ = "twoway"
    _in_type_ = "bookmark"
    _out_type_ = "bookmark"
    _icon_ = "nautilus"
    _configurable_ = True

    def __init__(self):
        DataProvider.TwoWay.__init__(self)
        self._bookmarks = []
        self._bookmarksFile = os.path.expanduser("~/.gtk-bookmarks")
        self.update_configuration(
            syncLocal = False,
            syncRemote = True
        )

    def _split_bookmarks_string(self, string):
        try:
            (uri, title) = string.split(" ", 1)
        except ValueError:
            (uri, title) = (string, string.split("/")[-1])
        return (title.replace("\n", ""), uri.replace("\n", ""))

    def _join_bookmarks_string(self, title, uri):
        if uri.split("/")[-1] == title:
            return uri+"\n"
        else:
            return "%s %s\n" % (uri, title)

    def _regenerate_bookmarks_file(self):
        # CAUTION: serious crack follows
        bookmarks_file_new_content = [] # new file content
        # Here we transfer the contents of the old file to the new
        for line in file(self._bookmarksFile, "r"):
            (title, uri) = self._split_bookmarks_string(line)
            if not self.is_local_uri(uri) and not self.syncRemote:
                # This is a remote uri and remote uri's are not being sync'ed
                # we'll keep it in the new file instead of removing it
                bookmarks_file_new_content.append(self._join_bookmarks_string(title, uri))
            elif self.is_local_uri(uri) and not self.syncLocal:
                # This is a local uri and local uri's are not being sync'ed
                # we'll keep it in the new file instead of removing it
                bookmarks_file_new_content.append(self._join_bookmarks_string(title, uri))
        # Now we transfer the bookmarks from self._bookmarks to the new file
        for bookmark in self._bookmarks:
            (title, uri) = (bookmark.get_title(), bookmark.get_uri())
            bookmark_string = self._join_bookmarks_string(title, uri)
            if not bookmark_string in bookmarks_file_new_content:
                bookmarks_file_new_content.append(bookmark_string)
        # Write bookmarks_file_new_content to file
        file(self._bookmarksFile, "w").writelines(bookmarks_file_new_content)

    def _join_bookmarks_string(self, luid, new_bookmark):
        for bookmark in self._bookmarks:
            if bookmark.get_UID() == luid:
                bookmark = new_bookmark

    def _put_bookmark(self, bookmark):
        bookmark.set_UID(bookmark.get_hash())
        self._bookmarks.append(bookmark)
        return bookmark.get_UID()

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self._bookmarks = []
        for line in file(self._bookmarksFile):
            (title, uri) = self._split_bookmarks_string(line)
            if self.is_local_uri(uri):
                if not self.syncLocal:
                    continue
            elif not self.syncRemote:
                    continue
            self._put_bookmark(Bookmark.Bookmark(title, uri))


    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        retval = []
        for bookmark in self._bookmarks:
            retval.append(bookmark.get_UID())
        return retval
        
    def get(self, luid):
        DataProvider.TwoWay.get(self, luid)
        for bookmark in self._bookmarks:
            if bookmark.get_UID() == luid:
                return bookmark

    def put(self, bookmark, overwrite, luid=None):
        # thanks to the wiki for most of this
        DataProvider.TwoWay.put(self, bookmark, overwrite, luid)
        if overwrite and luid:
            luid = self._join_bookmarks_string(luid, data)
        else:
            if luid == luid in self.get_all():
                old_bookmark = self.get(luid)
                comp = bookmark.compare(old_bookmark)
                # Possibility 1: If LUID != None (i.e this is a modification/update of a 
                # previous sync, and we are newer, then go ahead an put the data
                if luid != None and comp == conduit.datatypes.COMPARISON_NEWER:
                     LUID = self._join_bookmarks_string(luid, bookmark)
                     self._regenerate_bookmarks_file()
                # Possibility 3: We are the same, so return either rid
                elif comp == conduit.datatypes.COMPARISON_EQUAL:
                    return old_bookmark.get_rid()
                # Possibility 2, 4: All that remains are conflicts
                else:
                    raise Exceptions.SynchronizeConflictError(comp , bookmark, old_bookmark)
            else:
                # Possibility 5:
                luid = self._put_bookmark(bookmark)
                self._regenerate_bookmarks_file()
        # now return the rid
        if not luid:
            raise Exceptions.SyncronizeError(_("Error putting/updating bookmark"))
        else:
            return self.get(luid).get_rid()

    def is_local_uri(self, uri):
        if uri.startswith("file://"):
            return True
        return False

    def config_setup(self, config):
        config.add_item("Sync bookmarks to local places/files", "check", 
            config_name = "syncLocal"
        )
        config.add_item("Sync bookmarks to remote places/files", "check", 
            config_name = "syncRemote"
        )

    def get_UID(self):
        return Utils.get_user_string()

