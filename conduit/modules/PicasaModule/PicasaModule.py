"""
Picasa Uploader.
"""
import os, sys
import traceback
import md5
import logging
log = logging.getLogger("modules.Picasa")

import conduit
import conduit.Utils as Utils
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Photo as Photo

Utils.dataprovider_add_dir_to_path(__file__, "PicasaAPI")
from picasaweb import PicasaWeb

from gettext import gettext as _

MODULES = {
    "PicasaTwoWay" :          { "type": "dataprovider" }        
}

class PicasaTwoWay(Image.ImageTwoWay):

    _name_ = _("Picasa")
    _description_ = _("Sync your Google Picasa photos")
    _icon_ = "picasa"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.need_configuration(True)
        
        self.username = ""
        self.password = ""
        self.album = ""
        self.imageSize = "None"

        self.gapi = None
        self.galbum = None
        self.gphotos = None

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo.url

    def _get_photo_info (self, id):
        if self.gphotos.has_key(id):
            return self.gphotos[id]
        else:
            return None
            
    def _get_photo_formats (self):
        return ("image/jpeg", )
        
    def refresh(self):
        Image.ImageTwoWay.refresh(self)
        self.gapi = PicasaWeb(self.username, self.password)

        albums = self.gapi.getAlbums ()
        if not albums.has_key (self.album):
            self.galbum = self.gapi.createAlbum (self.album, public=False)
        else:
            self.galbum = albums[self.album]

        self.gphotos = self.galbum.getPhotos()


    def get_all (self):
        return self.gphotos.keys()

    def get (self, LUID):
        Image.ImageTwoWay.get (self, LUID)
        gphoto = self.gphotos[LUID]

        f = Photo.Photo (URI=gphoto.url)
        f.force_new_mtime(gphoto.timestamp)
        f.set_open_URI(gphoto.url)
        f.set_UID(LUID)

        return f

    def delete(self, LUID):
        if not self.gphotos.has_key(LUID):
            log.warn("Photo does not exit")
            return

        self.galbum.deletePhoto (self.gphotos[LUID])
        del self.gphotos[LUID]

    def _upload_photo (self, uploadInfo):
        try:
            ret = self.galbum.uploadPhoto(uploadInfo.url, uploadInfo.mimeType, uploadInfo.name)

            for tag in uploadInfo.tags:
                ret.addTag (str(tag))

            return Rid(uid=ret.id)
        except Exception, e:
            raise Exceptions.SyncronizeError("Picasa Upload Error.")

    def _get_photo_size (self):
        return self.imageSize
        
    def configure(self, window):
        """
        Configures the PicasaTwoWay
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "PicasaTwoWayConfigDialog")
                        
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
        
        dlg = widget.get_widget("PicasaTwoWayConfigDialog")
        
        response = Utils.run_dialog (dlg, window)

        if response == True:
            self.username = username.get_text()
            self.password = password.get_text()
            self.album = album.get_text()

            self.imageSize = self._resize_combobox_get_active(resizecombobox)

            self.set_configured(self.is_configured())

        dlg.destroy()    
        
    def get_configuration(self):
        return {
            "imageSize" : self.imageSize,
            "username" : self.username,
            "password" : self.password,
            "album" : self.album
            }
            
    def is_configured (self):
        if len(self.username) < 1:
            return False
        
        if len(self.password) < 1:
            return False
            
        if len(self.album) < 1:
            return False
            
        return True

    def get_UID(self):
        return self.username
            
