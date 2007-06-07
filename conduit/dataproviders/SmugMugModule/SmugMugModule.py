"""
SmugMug Uploader.
"""
import os, sys
import gtk
import traceback
import md5


import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

Utils.dataprovider_add_dir_to_path(__file__, "SmugMugAPI")
from smugmug import SmugMug

MODULES = {
    "SmugMugSink" :          { "type": "dataprovider" }        
}

class SmugMugSink(DataProvider.ImageSink):

    _name_ = "SmugMug"
    _description_ = "Sync Your SmugMug.com Photos"
    _module_type_ = "sink"
    _icon_ = "smugmug"

    def __init__(self, *args):
        DataProvider.ImageSink.__init__(self)
        self.need_configuration(True)
        
        self.password = ""
        self.album = ""
        self.sapi = None

    def _get_photo_info (self, photoId):
        return self.sapi.get_image_info (photoId)

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo['OriginalURL']
        
    def refresh(self):
        DataProvider.ImageSink.refresh(self)
        self.sapi = SmugMug(self.username, self.password)

    def upload_photo (self, url, name):
       # upload to album; and return image id here
        try:
            albumID = self.get_album_id ()
            return self.sapi.upload_file( albumID, url, name )
        except:
            raise Exceptions.SyncronizeError("SmugMug Upload Error.")
 
    def configure(self, window):
        """
        Configures the SmugMugSink
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "SmugMugSinkConfigDialog")
                        
        #get a whole bunch of widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        album = widget.get_widget("album")                
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)
        album.set_text (self.album)
        
        dlg = widget.get_widget("SmugMugSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()

        if response == gtk.RESPONSE_OK:
            self.username = username.get_text()
            self.password = password.get_text()
            self.album = album.get_text()

            self.set_configured(self.is_configured())

        dlg.destroy()    
        
    def get_configuration(self):
        return {
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

    def get_album_id (self):
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
            
