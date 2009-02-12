"""
SmugMug Uploader.
"""
import os, sys
import traceback
import md5
import logging
log = logging.getLogger("modules.SmugMug")

import conduit
import conduit.utils as Utils
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Photo as Photo

Utils.dataprovider_add_dir_to_path(__file__, "SmugMugAPI")
from smugmug import SmugMug, SmugMugException

from gettext import gettext as _

MODULES = {
    "SmugMugTwoWay" :          { "type": "dataprovider" }        
}

class SmugMugTwoWay(Image.ImageTwoWay):

    _name_ = _("SmugMug")
    _description_ = _("Synchronize your SmugMug.com photos")
    _module_type_ = "twoway"
    _icon_ = "smugmug"
    _configurable_ = True

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.username = ""
        self.password = ""
        self.album = ""
        self.imageSize = "None"
        self.sapi = None

    def _get_photo_info (self, photoId):
        try:
            return self.sapi.get_image_info (photoId)
        except SmugMugException, e:
            log.warn ("Get info error: %s" % e.get_printable_error())
            return None

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo['OriginalURL']
        
    def _upload_photo (self, uploadInfo):
        """
        Upload to album; and return image id here
        """
        try:
            albumID = self._get_album_id ()
            uid = self.sapi.upload_file( albumID, uploadInfo.url, uploadInfo.name)
            return Rid(uid=uid)
        except:
            raise Exceptions.SyncronizeError("SmugMug Upload Error.")

    def refresh(self):
        Image.ImageTwoWay.refresh(self)

        # make sure we logout from previous logins
        if self.sapi:
            self.sapi.logout()

        # login to smugmug
        try:
            self.sapi = SmugMug(self.username, self.password)
        except SmugMugException, e:
            raise Exceptions.RefreshError (e.get_printable_error())


    def get_all (self):
        return self.sapi.get_images (self._get_album_id())


    def get (self, LUID):
        simage = self.sapi.get_image_info(LUID)
        url = simage['OriginalURL']

        f = Photo.Photo(URI=url)
        f.force_new_filename(simage['FileName'])
        f.set_open_URI(url)
        f.set_UID(LUID)

        return f

    def delete(self, LUID):
        """
        Use LUID to delete from smugmug album
        """
        try:
            self.sapi.delete_image(LUID)
        except SmugMugException, e:
            log.warn('Delete error: %s' % e.get_printable_error())

    def _get_photo_size (self):
        return self.imageSize
 
    def config_setup(self, config):
        config.add_section("Account")
        config.add_item("Email", "text",
            config_name = "username"
        )
        config.add_item("Password", "text",
            config_name = "password",
            password = True
        ) 
        config.add_section("Saved photos settings")
        config.add_item("Album", "text",
            config_name = "album",
        )
        config.add_item("Resize photos", "combo",
            choices = [("None", "No resize"), ("640x480", "640x480"), ("800x600", "800x600"), ("1024x768", "1024x768")],
            config_name = "imageSize"
        )
 
    def configure_(self, window):
        """
        Configures the SmugMugTwoWay
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "SmugMugTwoWayConfigDialog")
                        
        #get a whole bunch of widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        album = widget.get_widget("album")                
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)
        album.set_text (self.album)

        resizecombobox = widget.get_widget("combobox1")
        self._resize_combobox_build(resizecombobox, self.imageSize)
        
        dlg = widget.get_widget("SmugMugTwoWayConfigDialog")

        dlg.set_transient_for(window)
        
        response = Utils.run_dialog (dlg, window)

        if response == True:
            self.username = username.get_text()
            self.password = password.get_text()
            self.album = album.get_text()
            self.imageSize = self._resize_combobox_get_active(resizecombobox)
        dlg.destroy()    
        
    def get_configuration(self):
        return {
            "imageSize" : self.imageSize,
            "username" : self.username,
            "password" : self.password,
            "album" : self.album
            }
            
    def is_configured (self, isSource, isTwoWay):
        if len(self.username) < 1:
            return False
        
        if len(self.password) < 1:
            return False
            
        if len(self.album) < 1:
            return False
            
        return True

    def _get_album_id (self):
        """
        Tries to retrieve a valid album id, and creates
        a new one if it does not exist yet
        """
        id = 0
        
        # see if album already exists
        albums = self.sapi.get_albums()

        if albums.has_key (self.album):
            id = albums[self.album]
    
        # return if it does
        if id != 0:
            return id
        # create otherwise
        else:
            return self.sapi.create_album (self.album)     

    def get_UID(self):
        return self.username
            
