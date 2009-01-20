# Copyright 2009 - Andrew Stomont <andyjstormont@googlemail.com>

import logging
log = logging.getLogger( "modules.NautilusBookmarks" )

import conduit
import conduit.dataproviders.DataProvider as DataProvider
from conduit.datatypes.Bookmark import Bookmark

import os

MODULES = {
    "NautilusBookmarksDataProviderTwoWay" : { "type": "dataprovider" }
}

class NautilusBookmarksDataProviderTwoWay( DataProvider.TwoWay ):

    _name_ = "Nautilus Bookmarks"
    _description_ = "Sync your Nautilus Bookmarks"
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "bookmark"
    _out_type_ = "bookmark"
    _icon_ = "applications-internet"
    _configurable_ = True

    def __init__( self ):
        self.Bookmarks = []
        self.Sync_Local = False
        self.Sync_Remote = True
        DataProvider.TwoWay.__init__( self )

    def refresh( self ):
        self.Bookmarks = []
        self.Bookmarks_file = os.path.expanduser( "~/.gtk-bookmarks" )
        for line in file( self.Bookmarks_file ):
            ( title, uri ) = self.split_bookmarks_string( line )
            if self.is_local_uri( uri ):
                if not self.Sync_Local:
                    continue
            elif not self.Sync_Remote:
                    continue
            self.put_bookmark( Bookmark( title, uri ) )
        DataProvider.TwoWay.refresh( self )

    def get_all( self ):
        DataProvider.TwoWay.get_all( self )
        retval = []
        for bookmark in self.Bookmarks:
            retval.append( bookmark.get_UID() )
        return retval
        
    def get( self, luid ):
        DataProvider.TwoWay.get( self, luid )
        for bookmark in self.Bookmarks:
            if bookmark.get_UID() == luid:
                return bookmark

    def put( self, bookmark, overwrite, luid=None ):
        # thanks to the wiki for most of this
        DataProvider.TwoWay.put( self, bookmark, overwrite, luid )
        if overwrite and luid:
            luid = self.replace_bookmark( luid, data )
        else:
            if luid == luid in self.get_all():
                old_bookmark = self.get( luid )
                comp = bookmark.compare( old_bookmark )
                # Possibility 1: If LUID != None (i.e this is a modification/update of a 
                # previous sync, and we are newer, then go ahead an put the data
                if luid != None and comp == conduit.datatypes.COMPARISON_NEWER:
                     LUID = self.replace_bookmark( luid, bookmark )
                     self.regenerate_bookmarks_file()
                # Possibility 3: We are the same, so return either rid
                elif comp == conduit.datatypes.COMPARISON_EQUAL:
                    return old_bookmark.get_rid()
                # Possibility 2, 4: All that remains are conflicts
                else:
                    raise Exceptions.SynchronizeConflictError( comp , bookmark, old_bookmark )
            else:
                # Possibility 5:
                luid = self.put_bookmark( bookmark )
                self.regenerate_bookmarks_file()
        # now return the rid
        if not luid:
            raise Exceptions.SyncronizeError("Error putting/updating bookmark")
        else:
            return self.get( luid ).get_rid()

    def split_bookmarks_string( self, string ):
        try:
            ( uri, title ) = string.split( " ", 1 )
        except ValueError:
            ( uri, title ) = ( string, string.split( "/" )[-1] )
        return ( title.replace( "\n", "" ), uri.replace( "\n", "" ) )

    def join_bookmarks_string( self, title, uri ):
        if uri.split( "/" )[-1] == title:
            return uri+"\n"
        else:
            return "%s %s\n" % ( uri, title )

    def regenerate_bookmarks_file( self ):
        # CAUTION: serious crack follows
        bookmarks_file_new_content = [] # new file content
        # Here we transfer the contents of the old file to the new
        for line in file( self.Bookmarks_file, "r" ):
            ( title, uri ) = self.split_bookmarks_string( line )
            if not self.is_local_uri( uri ) and not self.Sync_Remote:
                # This is a remote uri and remote uri's are not being sync'ed
                # we'll keep it in the new file instead of removing it
                bookmarks_file_new_content.append( self.join_bookmarks_string( title, uri ) )
            elif self.is_local_uri( uri ) and not self.Sync_Local:
                # This is a local uri and local uri's are not being sync'ed
                # we'll keep it in the new file instead of removing it
                bookmarks_file_new_content.append( self.join_bookmarks_string( title, uri ) )
        # Now we transfer the bookmarks from self.Bookmarks to the new file
        for bookmark in self.Bookmarks:
            ( title, uri ) = ( bookmark.get_title(), bookmark.get_uri() )
            bookmark_string = self.join_bookmarks_string( title, uri )
            if not bookmark_string in bookmarks_file_new_content:
                bookmarks_file_new_content.append( bookmark_string )
        # Write bookmarks_file_new_content to file
        file( self.Bookmarks_file, "w" ).writelines( bookmarks_file_new_content )

    def replace_bookmark( self, luid, new_bookmark ):
        for bookmark in self.Bookmarks:
            if bookmark.get_UID() == luid:
                bookmark = new_bookmark

    def put_bookmark( self, bookmark ):
        bookmark.set_UID( bookmark.get_hash() )
        self.Bookmarks.append( bookmark )
        return bookmark.get_UID()

    def get_UID( self ):
        return "NautilusBookmarks"

    def set_remote_syncing( self, value ):
        self.Sync_Remote = value

    def set_local_syncing( self, value ):
        self.Sync_Local = value

    def is_local_uri( self, uri ):
        if uri.startswith( "file://" ):
            return True
        return False

    def configure( self, window ):
        # Thanks to the wiki for this
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator
        items = [
            {
                "Name" : "Sync bookmarks to local places/files",
                "Kind" : "check",
                "Callback" : self.set_local_syncing,
                "InitialValue" : self.Sync_Local
            },
            {
                "Name" : "Sync bookmarks to remote places/files",
                "Kind" : "check",
                "Callback" : self.set_remote_syncing,
                "InitialValue" : self.Sync_Remote
            }
        ]
        dialog = SimpleConfigurator.SimpleConfigurator( window, self._name_, items )
        dialog.run()

    def get_configuration( self ):
        return { "Sync_Local" : self.Sync_Local, "Sync_Remote" : self.Sync_Remote }
