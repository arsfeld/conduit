# Copyright 2009 - Andrew Stormont <andyjstormont@googlemail.com>

import os
from ConfigParser import ConfigParser
import sqlite3
import logging
import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
from conduit.datatypes.Bookmark import Bookmark
import conduit.Exceptions as Exceptions

log = logging.getLogger("modules.Firefox3")

MODULES = {
    "Firefox3DataProviderSource" : { "type" : "dataprovider" },
}

class Firefox3DataProviderSource( DataProvider.DataSource ):
    """ 
    Firefox 3 Bookmarks datasource
    """

    _name_ = "Firefox 3 Bookmarks"
    _description_ = "Syncronize your Firefox 3 Bookmarks"
    _category_ = conduit.dataproviders.CATEGORY_BOOKMARKS
    _module_type_ = "source"
    _out_type_ = "bookmark"
    _icon_ = "applications-internet"
    _configurable_ = True

    # nasty constants
    SYNCERROR = "Can't read Firefox 3 Bookmarks - please make sure Firefox is closed."
    ( BOOKMARKS_ROOT, BOOKMARKS_MENU, BOOKMARKS_TOOLBAR ) = range( 1,4 )

    def __init__( self ):
        self.Bookmarks = []

        self.FirefoxDir = os.path.expanduser( "~/.mozilla/firefox/" )
        self.Cf = ConfigParser()
        self.Cf.read( self.FirefoxDir + "profiles.ini" )
        self.ProfilePath = self.Cf.get( "Profile0", "Path" ) # default
        DataProvider.DataSource.__init__( self )

    def refresh( self ):
        # sqlite3 is not thread safe, so we cannot preserve connections in this class
        Con = sqlite3.connect( self.FirefoxDir + self.ProfilePath + "/places.sqlite" )
        try:
            Cur = Con.execute( "select * from moz_bookmarks" )
        except:
            log.debug( self.SYNCERROR )
            raise Exceptions.SyncronizeError( self.SYNCERROR )
        for Line in Cur.fetchall():
            ( bid, btype, fk, parent, position, title, keywordid, folder_type, dateadded, lastmodified ) = Line
            if not fk:
                # this bookmark has no url, that means it's a folder or something firefox specific
                continue
            else:
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
            log.debug( self.SYNCERROR )
            raise Exceptions.SyncronizeError( self.SYNCERROR )
        retval = None
        for Line in Cur.fetchall():
            ( bid, url, title, host, visits, hidden, typed, faviconid, frecency ) = Line
            if bid == fk:
                retval = url
                break
        Con.close()
        return retval

    def configure( self, window ):
        # thanks to the evolution module for some of this
        import gtk
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "Firefox3ConfigDialog"
                        )

        sourceComboBox = tree.get_widget("profileComboBox")
        store = gtk.ListStore( str, str )
        sourceComboBox.set_model(store)

        cell = gtk.CellRendererText()
        sourceComboBox.pack_start(cell, True)
        sourceComboBox.add_attribute(cell, 'text', 0)
        sourceComboBox.set_active(0)

        for profilename, profilepath in self.get_profiles():
            rowref = store.append( ( profilename, profilepath ) )
            if profilepath == self.ProfilePath:
                sourceComboBox.set_active_iter(rowref)

        dlg = tree.get_widget("Firefox3ConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.ProfilePath = store.get_value(sourceComboBox.get_active_iter(), 1)
        dlg.destroy()

    def get_profiles( self ):
        retval = []
        for section in self.Cf.sections():
            if section != "General":
                retval.append( ( self.Cf.get( section, "Name" ), self.Cf.get( section, "Path" ) ) )
        return retval

    def get_configuration(self):
        return { "ProfilePath" : self.ProfilePath }

    def set_configuration(self, config):
        self.ProfilePath = config.get( "ProfilePath", self.ProfilePath )

    def get_UID( self ):
        return "Firefox3Module"
            
