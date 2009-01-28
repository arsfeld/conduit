# Copyright 2009 - Andrew Stomont <andyjstormont@googlemail.com>

import logging
log = logging.getLogger( "modules.GoogleBookmarks" )

import conduit
import conduit.dataproviders.DataProvider as DataProvider
from conduit.datatypes.Bookmark import Bookmark
import conduit.Web as Web

import urllib2
from xml.dom.minidom import parse

MODULES = {
    "GoogleBookmarksDataProviderSource" : { "type": "dataprovider" }
}

class GoogleBookmarksDataProviderSource( DataProvider.DataSource ):

    _name_ = "Google Bookmarks"
    _description_ = "Sync your Google Bookmarks"
    _category_ = conduit.dataproviders.CATEGORY_BOOKMARKS
    _module_type_ = "source"
    _out_type_ = "bookmark"
    _icon_ = "applications-internet"
    _configurable_ = True

    def __init__( self ):
        self.Bookmarks = []
        self.username = ""
        self.password = ""
        DataProvider.DataSource.__init__( self )

    def refresh( self ):
        #self.Bookmarks = []
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password( 'Google Search History', 'www.google.com', self.username, self.password )
        opener = urllib2.build_opener( auth_handler )
        bookmark_feed = opener.open( "https://www.google.com/bookmarks/?output=rss" )
        for item in parse( bookmark_feed ).documentElement.getElementsByTagName( "item" ):
            title = item.getElementsByTagName( "title" )[0].childNodes[0].data
            link = item.getElementsByTagName( "link" )[0].childNodes[0].data
            bookmark = Bookmark( title, link )
            bookmark.set_UID( bookmark.get_hash() )
            self.Bookmarks.append( bookmark )
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

    def get_UID( self ):
        return "GoogleBookmarks"

    def configure( self, window ):
        # Thanks to the wiki for this
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        PasswordEntry = gtk.Entry()
        gtk.Entry().set_visibility( False )

        items = [
            {
                "Name" : "Username",
                "Kind" : "text",
                "Callback" : self.set_username,
                "InitialValue" : str( self.username )
            },           
            {
                "Name" : "Password",
                "Kind" : "password",
                "Callback" : self.set_password,
                "InitialValue" : str( self.password )
            }                             
        ]
        dialog = SimpleConfigurator.SimpleConfigurator( window, self._name_, items )
        dialog.run()
        self.refresh()

    def set_username( self, username ):
        self.username = username

    def set_password( self, password ):
        self.password = password

    def get_configuration( self ):
        return { "username" : self.username, "password" : self.password }
