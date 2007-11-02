"""
Facebook Photo Uploader.
"""
import os, sys
import traceback
import md5

import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.Web as Web
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

Utils.dataprovider_add_dir_to_path(__file__)
from pyfacebook import Facebook, FacebookError

MODULES = {
    "FacebookSink" :          { "type": "dataprovider" }        
}

class FacebookSink(Image.ImageSink):

    _name_ = "Facebook"
    _description_ = "Sync Your Facebook Photos"
    _module_type_ = "sink"
    _icon_ = "facebook"

    API_KEY="6ce1868c3292471c022c771c0d4d51ed"
    SECRET="20e2c82829f1884e40efc616a44e5d1f"

    def __init__(self, *args):
        Image.ImageSink.__init__(self)
        self.fapi = None

    def _upload_photo (self, uploadInfo):
        """
        Upload to album; and return image id here
        """
        try:
            rsp = self.fapi.photos.upload(uploadInfo.url)
            return rsp["pid"]
        except FacebookError, f:
            raise Exceptions.SyncronizeError("Facebook Upload Error %s" % f)

    def _login(self):
        """
        Get ourselves a token we can use to perform all calls
        """
        self.fapi = Facebook(FacebookSink.API_KEY, FacebookSink.SECRET)
        self.fapi.auth.createToken()
        url = self.fapi.get_login_url()

        #wait for log in
        Web.LoginMagic("Log into Facebook", url, login_function=self._try_login, browser="gtkmozembed")

    def _try_login(self):
        """
        This function is used by the login tester, we try to get a token,
        but return None if it does not succeed so the login tester can keep trying
        """
        print "Trying Login"        
        rsp = self.fapi.auth.getSession()
        return rsp.has_key("secret") and rsp.has_key("session_key")

    def refresh(self):
        Image.ImageSink.refresh(self)
        if self.fapi == None:
            self._login()

    def is_configured (self):
        return True

    def get_UID(self):
        return ""
        return self.fapi.uid
            
