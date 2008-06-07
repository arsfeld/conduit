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
    _description_ = _("Sync your Facebook photos")
    _module_type_ = "sink"
    _icon_ = "facebook"

    API_KEY="6ce1868c3292471c022c771c0d4d51ed"
    SECRET="20e2c82829f1884e40efc616a44e5d1f"

    def __init__(self, *args):
        Image.ImageSink.__init__(self)
        self.fapi = pyfacebook.Facebook(FacebookSink.API_KEY, FacebookSink.SECRET)
        self.browser = "gtkmozembed"

    def _upload_photo (self, uploadInfo):
        """
        Upload to album; and return image id here
        """
        try:
            rsp = self.fapi.photos.upload(uploadInfo.url)
            return Rid(uid=rsp["pid"])
        except pyfacebook.FacebookError, f:
            raise Exceptions.SyncronizeError("Facebook Upload Error %s" % f)
            
    def _get_albums(self):
        albums = []
        try:
            for a in self.fapi.photos.getAlbums(self.fapi.uid):
                albums.append((a['name'], a['aid']))
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
        
    def refresh(self):
        Image.ImageSink.refresh(self)
        if self.fapi.uid == None:
            self._login()

    def get_UID(self):
        if self.fapi.uid == None:
            return ""
        return self.fapi.uid
            
