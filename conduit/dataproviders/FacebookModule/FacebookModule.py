"""
Facebook Photo Uploader.
"""
import os, sys
import gtk
import traceback
import md5
import gnome

import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

Utils.dataprovider_add_dir_to_path(__file__)
from pyfacebook import Facebook, FacebookError

MODULES = {
    "FacebookSink" :          { "type": "dataprovider" }        
}

class FacebookSink(DataProvider.ImageSink):

    _name_ = "Facebook"
    _description_ = "Sync Your Facebook Photos"
    _module_type_ = "sink"
    _icon_ = "facebook"

    API_KEY="6ce1868c3292471c022c771c0d4d51ed"
    SECRET="20e2c82829f1884e40efc616a44e5d1f"

    def __init__(self, *args):
        DataProvider.ImageSink.__init__(self)
        self.fapi = None

    def _upload_photo (self, url, name):
        """
        Upload to album; and return image id here
        """
        try:
            rsp = self.fapi.photos.upload(url)
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

        gnome.url_show(url)

        # wait for user to login
        login_tester = Utils.LoginTester(self._try_login)
        login_tester.wait_for_login()

    def _try_login(self):
        """
        This function is used by the login tester, we try to get a token,
        but return None if it does not succeed so the login tester can keep trying
        """
        try:
            self.fapi.auth.getSession()
            return True
        except:
            return None

    def refresh(self):
        DataProvider.ImageSink.refresh(self)
        if self.fapi == None:
            self._login()

    def is_configured (self):
        return True

    def get_UID(self):
        return ""
        return self.fapi.uid
            
