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
from smugmug import SmugMug, SmugMugException

MODULES = {
    "SmugMugTwoWay" :          { "type": "dataprovider" }        
}

class SmugMugTwoWay(DataProvider.ImageTwoWay):

    _name_ = "SmugMug"
    _description_ = "Sync Your SmugMug.com Photos"
    _module_type_ = "twoway"
    _icon_ = "smugmug"

    def __init__(self, *args):
        DataProvider.ImageTwoWay.__init__(self)
        self.need_configuration(True)
        
        self.password = ""
        self.album = ""
        self.sapi = None

    def _get_photo_info (self, photoId):
        try:
            return self.sapi.get_image_info (photoId)
        except SmugMugException, e:
            logw ("Get info error: %s" % e.get_printable_error())
            return None

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo['OriginalURL']
        
    def _upload_photo (self, url, mimeType, name):
        """
        Upload to album; and return image id here
        """
        try:
            albumID = self._get_album_id ()
            return self.sapi.upload_file( albumID, url, name )
        except:
            raise Exceptions.SyncronizeError("SmugMug Upload Error.")

    def refresh(self):
        DataProvider.ImageTwoWay.refresh(self)

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

        f = File.File(URI=url)
        f.force_new_filename(simage['FileName'])
        f.set_open_URI (url)
        f.set_UID(LUID)

        return f

    def delete(self, LUID):
        """
        Use LUID to delete from smugmug album
        """
        try:
            self.sapi.delete_image(LUID)
        except SmugMugException, e:
            logw('Delete error: %s' % e.get_printable_error())
 
    def configure(self, window):
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
        
        dlg = widget.get_widget("SmugMugTwoWayConfigDialog")

        dlg.set_transient_for(window)
        
        response = Utils.run_dialog (dlg, window)

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
            
