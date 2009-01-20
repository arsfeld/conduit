# Copyright 2009 - Andrew Stormont <andyjstormont@googlemail.com>

import os
from ConfigParser import ConfigParser
import sqlite3
import logging
import conduit
import conduit.dataproviders.DataProvider as DataProvider
from conduit.datatypes.Bookmark import Bookmark
import conduit.Exceptions as Exceptions

log = logging.getLogger("modules.Firefox3")

MODULES = {
    "Firefox3DataProviderSource" : { "type" : "dataprovider" },
}

FFSYNCERROR = "Can't read Firefox 3 Bookmarks - please make sure Firefox is closed."

class Firefox3DataProviderSource( DataProvider.DataSource ):
    """ 
    Firefox 3 Bookmarks datasource
    """

    _name_ = "Firefox 3 Bookmarks"
    _description_ = "Sync your Firefox 3 Bookmarks"
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _out_type_ = "bookmark"
    _icon_ = "applications-internet"

    def __init__( self ):
        self.FirefoxDir = os.path.expanduser( "~/.mozilla/firefox/" )
        Cf = ConfigParser()
        Cf.read( self.FirefoxDir + "profiles.ini" )
        self.ProfilePath = Cf.get( "Profile0", "Path" )
        self.Bookmarks = []
        DataProvider.DataSource.__init__( self )

    def refresh( self ):
        Con = sqlite3.connect( self.FirefoxDir + self.ProfilePath + "/places.sqlite" )
        try:
            Cur = Con.execute( "select * from moz_bookmarks" )
        except:
            log.debug( FFSYNCERROR )
            raise Exceptions.SyncronizeError( FFSYNCERROR )
        for Line in Cur.fetchall():
            ( bid, btype, fk, parent, position, title, keywordid, foldertype, dateadded, lastmodified ) = Line
            bookmark = Bookmark( title, self.get_bookmark_url_from_fk( fk ) )
            bookmark.set_UID( bookmark.get_hash() )
            self.Bookmarks.append( bookmark )
        Con.close()  
        DataProvider.DataSource.refresh( self )    

    def get_all( self ):
        DataProvider.DataSource.get_all( self )
        retval = []
        for bookmark in self.Bookmarks:
            retval.append( bookmark.get_UID() )
        return retval

    def get( self, luid ):
        DataProvider.DataSource.get( self, luid )
        for bookmark in self.Bookmarks:
            if bookmark.get_UID() == luid:
                return bookmark

    def get_bookmark_url_from_fk( self, fk ):
        Con = sqlite3.connect( self.FirefoxDir + self.ProfilePath + "/places.sqlite" )
        try:
            Cur = Con.execute( "select * from moz_places" )
        except:
            log.debug( FFSYNCERROR )
            raise Exceptions.SyncronizeError( FFSYNCERROR )
        retval = None
        for Line in Cur.fetchall():
            ( bid, url, title, host, visits, hidden, typed, faviconid, frecency ) = Line
            if bid == fk:
                retval = url
                break
        Con.close()
        return retval

    def get_UID( self ):
        return "Firefox3Module"
            
