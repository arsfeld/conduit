"""
Flickr Uploader.

Code Borrowed from postr, ross burtoni
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

Utils.dataprovider_add_dir_to_path(__file__, "FlickrAPI")
from flickrapi import FlickrAPI

MODULES = {
	"FlickrSink" :          { "type": "dataprovider" }        
}

class FlickrSink(DataProvider.DataSink):

    _name_ = "Flickr"
    _description_ = "Sync Your Flickr.com Photos"
    _category_ = DataProvider.CATEGORY_PHOTOS
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "flickr"

    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"
    ALLOWED_MIMETYPES = ["image/jpeg", "image/png"]
    
    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.need_configuration(True)
        
        self.username = ""
        self.fapi = None
        self.token = None
        self.tagWith = "Conduit"
        self.showPublic = True
        self.showFriends = True
        self.showFamily = True

    def _get_user_quota(self):
        """
        Returs used,total or -1,-1 on error
        """
        rsp = self.fapi.people_getUploadStatus(
                                api_key=FlickrSink.API_KEY, 
                                auth_token=self.token
                                )
        if self.fapi.getRspErrorCode(rsp) != 0:
            logd("Flickr people_getUploadStatus Error: %s" % self.fapi.getPrintableError(rsp))
            return -1,-1
        else:
            totalkb = rsp.user[0].bandwidth[0]["maxkb"]
            usedkb = rsp.user[0].bandwidth[0]["usedkb"]
            return int(usedkb),int(totalkb)

    def _get_photo_info(self, photoID):
        info = self.fapi.photos_getInfo(
                                    api_key=FlickrSink.API_KEY,
                                    photo_id=photoID
                                    )
        if self.fapi.getRspErrorCode(info) != 0:
            logd("Flickr photos_getInfo Error: %s" % self.fapi.getPrintableError(info))
            return None
        else:
            return info

    def _get_raw_photo_url(self, photoInfo):
        photo = photoInfo.photo[0]
        #photo is a dict so we can use pythons string formatting natively with
        #the correct keys
        url = "http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s.jpg" % photo
        return url
        
    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSink.refresh(self)
        self.fapi = FlickrAPI(FlickrSink.API_KEY, FlickrSink.SHARED_SECRET)
        self.token = self.fapi.getToken(self.username, browser="gnome-www-browser -p", perms="write")
        
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
        if mimeType not in FlickrSink.ALLOWED_MIMETYPES:
            raise Exceptions.SyncronizeError("Flickr does not allow uploading %s Files" % mimeType)
        
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
                    #Only upload the photo if it is newer than the Flickr one
                    url = self._get_raw_photo_url(info)
                    flickrFile = File.File(url)
                    #Flickr doesnt store the photo modification time anywhere, 
                    #so this is a limited test for equality type comparison
                    comp = photo.compare(flickrFile,True)
                    logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (photo.get_filename(),flickrFile.get_filename(),comp))
                    if comp != conduit.datatypes.COMPARISON_EQUAL:
                        raise Exceptions.SynchronizeConflictError(comp, photo, flickrFile)
                    else:
                        return LUID

        #We havent, or its been deleted so upload it
        logd("Uploading Photo URI = %s, Mimetype = %s, Original Name = %s" % 
            (photoURI, mimeType, originalName))
        ret = self.fapi.upload( api_key=FlickrSink.API_KEY, 
                                auth_token=self.token,
                                filename=photoURI,
                                title=originalName,
                                )
        if self.fapi.getRspErrorCode(ret) != 0:
            raise Exceptions.SyncronizeError("Flickr Upload Error: %s" % self.fapi.getPrintableError(ret))
        else:
            #return the photoID
            return ret.photoid[0].elementText

    def configure(self, window):
        """
        Configures the GmailSource for which emails it should return
        
        All the inner function foo is because the allEmail
        option is mutually exclusive with all the others (which may be
        mixed according to the users preferences
        """
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "FlickrSinkConfigDialog")
        
        #get a whole bunch of widgets
        attachTagCb = tree.get_widget("attach_tag_check")
        tagEntry = tree.get_widget("tag_entry")
        publicCb = tree.get_widget("public_check")
        friendsCb = tree.get_widget("friends_check")
        familyCb = tree.get_widget("family_check")
        username = tree.get_widget("username")
        
        #preload the widgets
        attachTagCb.set_active(len(self.tagWith) > 0)
        tagEntry.set_text(self.tagWith)
        publicCb.set_active(self.showPublic)
        friendsCb.set_active(self.showFriends)
        familyCb.set_active(self.showFamily)
        username.set_text(self.username)
        
        dlg = tree.get_widget("FlickrSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            if attachTagCb.get_active():
                self.tagWith = tagEntry.get_text()
            self.showPublic = publicCb.get_active()
            self.showFamily = familyCb.get_active()
            self.showFriends = friendsCb.get_active()                        
            self.username = username.get_text()

            #user must enter their username
            if len(self.username) > 0:
                self.set_configured(True)

        dlg.destroy()    
        
    def get_configuration(self):
        return {
            "username" : self.username,
            "tagWith" : self.tagWith,
            "showPublic" : self.showPublic,
            "showFriends" : self.showFriends,
            "showFamily" : self.showFamily
            }

    def set_configuration(self, config):
        DataProvider.DataSink.set_configuration(self, config)
        if len(self.username) != 0:
            self.set_configured(True)

    def get_UID(self):
        return self.token
            
