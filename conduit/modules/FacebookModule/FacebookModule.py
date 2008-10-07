"""
Facebook Photo Uploader.
"""
import os, sys
import traceback
import md5
import logging
log = logging.getLogger("modules.Facebook")

import conduit
import conduit.utils as Utils
import conduit.Web as Web
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.File as File

from gettext import gettext as _

try:
    import pyfacebook
except ImportError:
    Utils.dataprovider_add_dir_to_path(__file__)
    import pyfacebook
    
if pyfacebook.VERSION < '0.1':
    log.info("Facebook support disabled")
    MODULES = {}
else:
    log.info("Module Information: %s" % Utils.get_module_information(pyfacebook, 'VERSION'))
    MODULES = {
        "FacebookSink" :          { "type": "dataprovider" }        
    }

class FacebookSink(Image.ImageSink):

    _name_ = _("Facebook")
    _description_ = _("Synchronize your Facebook photos")
    _module_type_ = "sink"
    _icon_ = "facebook"
    _configurable_ = True

    API_KEY="6ce1868c3292471c022c771c0d4d51ed"
    SECRET="20e2c82829f1884e40efc616a44e5d1f"

    def __init__(self, *args):
        Image.ImageSink.__init__(self)
        self.fapi = pyfacebook.Facebook(FacebookSink.API_KEY, FacebookSink.SECRET)
        self.browser = "gtkmozembed"
        self.albumname = ""
        self.albums = {}

    def _upload_photo (self, uploadInfo):
        """
        Upload to album; and return image id here
        """
        try:
            rsp = self.fapi.photos.upload(
                                        uploadInfo.url,
                                        aid=self.albums.get(self.albumname, None))
            return Rid(uid=rsp["pid"])
        except pyfacebook.FacebookError, f:
            raise Exceptions.SyncronizeError("Facebook Upload Error %s" % f)
            
    def _get_albums(self):
        albums = {}
        try:
            for a in self.fapi.photos.getAlbums(self.fapi.uid):
                albums[a['name']] = a['aid']
        except pyfacebook.FacebookError, f:
            log.warn("Error getting album list: %s" % f)
        return albums
        
    def _get_photos(self, albumID):
        photos = {}
        try:
            for p in self.fapi.photos.get(aid=albumID):
                #only return big photos
                if p.get("src_big", ""):
                    photos[p['pid']] = p
        except pyfacebook.FacebookError, f:
            log.warn("Error getting photos from album %s list: %s" % (albumID,f))
        return photos
        
    def _get_photo_size (self):
        """
        Respect Facebooks largest image dimension of 604px
        http://wiki.developers.facebook.com/index.php/Photos.upload
        """
        return "604x604"        

    def _login(self):
        """
        Get ourselves a token we can use to perform all calls
        """
        self.fapi.auth.createToken()
        url = self.fapi.get_login_url()

        #wait for log in
        Web.LoginMagic("Log into Facebook", url, login_function=self._try_login, 
                browser=self.browser,       #instance var so tests can set it to system
                sleep_time=45,              #long sleep time to give time to login if using system browser
                )

    def _try_login(self):
        """
        This function is used by the login tester, we try to get a token,
        but return None if it does not succeed so the login tester can keep trying
        """
        log.info("Trying Login")
        rsp = self.fapi.auth.getSession()
        return rsp.has_key("secret") and rsp.has_key("session_key")
        
    def configure(self, window):
        import gtk
        import gobject
        def on_login_finish(*args):
            if self.fapi.uid:
                build_album_store()
            Utils.dialog_reset_cursor(dlg)
            
        def on_response(sender, responseID):
            if responseID == gtk.RESPONSE_OK:
                self.albumname = albumnamecombo.child.get_text()
                
        def load_button_clicked(button):
            Utils.dialog_set_busy_cursor(dlg)
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                                            self,
                                            on_login_finish,
                                            self._login)

        def build_album_store():
            album_store.clear()
            album_count = 0
            album_iter = None
            for album_name in self._get_albums().keys():
                iter = album_store.append((album_name,))
                if album_name != "" and album_name == self.albumname:
                    album_iter = iter
                album_count += 1

            if album_iter:
                albumnamecombo.set_active_iter(album_iter)
            elif self.albumname:
                albumnamecombo.child.set_text(self.albumname)
            elif album_count:
                albumnamecombo.set_active(0)

        tree = Utils.dataprovider_glade_get_widget(
                        __file__,
                        "config.glade",
                        "FacebookConfigDialog")

        #get a whole bunch of widgets
        albumnamecombo = tree.get_widget("albumnamecombo")
        load_button = tree.get_widget("load_button")
        dlg = tree.get_widget("FacebookConfigDialog")

        # setup combobox
        album_store = gtk.ListStore(gobject.TYPE_STRING)
        albumnamecombo.set_model(album_store)
        cell = gtk.CellRendererText()
        albumnamecombo.pack_start(cell, True)
        albumnamecombo.set_text_column(0)

        # load button
        load_button.connect('clicked', load_button_clicked)
        albumnamecombo.child.set_text(self.albumname)

        # run the dialog
        Utils.run_dialog_non_blocking(dlg, on_response, window)
        
    def refresh(self):
        Image.ImageSink.refresh(self)
        if self.fapi.uid == None:
            self._login()

        #get the list of albums
        if self.fapi.uid:
            self.albums = self._get_albums()
            if self.albumname and self.albumname not in self.albums:
                log.info("Creating album: %s" % self.albumname)
                try:
                    rsp = self.fapi.photos.createAlbum(
                                              #session_key=self.fapi.session_key,
                                              name=self.albumname)
                    self.albums[self.albumname] = rsp["aid"]
                except pyfacebook.FacebookError, f:
                    self.albumname = ""
                    log.warn("Error creating album: %s" % self.albumname)

    def get_UID(self):
        if self.fapi.uid == None:
            return ""
        return self.fapi.uid
        
    def is_configured (self, isSource, isTwoWay):
        #Specifing an album is optional
        return True

    def get_configuration(self):
        return {
            "albumname" : self.albumname
        }
            
