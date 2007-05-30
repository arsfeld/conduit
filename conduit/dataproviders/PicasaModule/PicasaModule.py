"""
Picasa Uploader.
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

Utils.dataprovider_add_dir_to_path(__file__, "PicasaAPI")
from picasaweb import PicasaWeb

MODULES = {
	"PicasaSink" :          { "type": "dataprovider" }        
}

class PicasaSink(DataProvider.DataSink):

    _name_ = "Picasa"
    _description_ = "Sync Your Google Picasa Photos"
    _category_ = DataProvider.CATEGORY_PHOTOS
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "picasa"

    ALLOWED_MIMETYPES = ["image/jpeg", "image/png"]
    
    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.need_configuration(True)
        
        self.username = ""
        self.password = ""
        self.album = ""
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
        
    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSink.refresh(self)
        self.gapi = PicasaWeb(self.username, self.password)

	albums = self.gapi.getAlbums ()
	if not albums.has_key (self.album):
	 	self.galbum = self.gapi.createAlbum (self.album, public=False)
	else:
	 	self.galbum = albums[self.album]

	self.gphotos = self.galbum.getPhotos()
        
    def put(self, photo, overwrite, LUID=None):
        """
        Accepts a vfs file. Must be made local.
        I also store a md5 of the photos uri to check for duplicates
        """
        DataProvider.DataSink.put(self, photo, overwrite, LUID)

        originalName = photo.get_filename()
        #Gets the local URI (/foo/bar). If this is a remote file then
        #it is first transferred to the local filesystem
        photoURI = photo.get_local_uri()

        mimeType = photo.get_mimetype()
        if mimeType not in PicasaSink.ALLOWED_MIMETYPES:
            raise Exceptions.SyncronizeError("Picasa does not allow uploading %s Files" % mimeType)

        #Check if we have already uploaded the photo
        if LUID != None:
            info = self._get_photo_info(LUID)
            #check if a photo exists at that UID
            if info != None:
                if overwrite == True:
                    #replace the photo
                    logw("REPLACE NOT IMPLEMENTED")
                    return LUID
                else:
                    #Only upload the photo if it is newer than the Picasa one
                    url = self._get_raw_photo_url(info)
                    picasaFile = File.File(url)
		    # Compare if they are the same size
                    comp = photo.compare(picasaFile,True)
                    logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (photo.get_filename(),picasaFile.get_filename(),comp))
                    if comp != conduit.datatypes.COMPARISON_EQUAL:
                        raise Exceptions.SynchronizeConflictError(comp, photo, smugmugFile)
                    else:
                        return LUID

        #We havent, or its been deleted so upload it
        logd("Uploading Photo URI = %s, Mimetype = %s, Original Name = %s" % 
            (photoURI, mimeType, originalName))
            
        # upload to album; and return image id here
        try:
	        ret = self.galbum.uploadPhoto(photoURI, originalName)
	        return ret.id
	except Exception, e:
		raise Exceptions.SyncronizeError("Picasa Upload Error.")

    def configure(self, window):
        """
        Configures the PicasaSink
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "PicasaSinkConfigDialog")
                        
        #get a whole bunch of widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        album = widget.get_widget("album")                
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)
        album.set_text (self.album)
        
        dlg = widget.get_widget("PicasaSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()

	print response

        if response == gtk.RESPONSE_OK:
            self.username = username.get_text()
            self.password = password.get_text()
            self.album = album.get_text()

            self.set_configured(self.is_config_valid())

        dlg.destroy()    
        
    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            "album" : self.album
            }
            
    def is_config_valid (self):
    	if len(self.username) < 1:
    		return False
    	
    	if len(self.password) < 1:
    		return False
    		
    	if len(self.album) < 1:
    		return False
    		
    	return True

    def set_configuration(self, config):
        DataProvider.DataSink.set_configuration(self, config)
        self.set_configured(self.is_config_valid ())

    def get_UID(self):
        return self.username
            
