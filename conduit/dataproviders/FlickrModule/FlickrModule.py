"""
Flickr Uploader.
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

class FlickrSink(DataProvider.ImageSink):

    _name_ = "Flickr"
    _description_ = "Sync Your Flickr.com Photos"
    _module_type_ = "sink"
    _icon_ = "flickr"

    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"
    
    def __init__(self, *args):
        DataProvider.ImageSink.__init__(self)
        self.need_configuration(True)
        
        self.fapi = None
        self.token = None
        self.tagWith = ""
        self.showPublic = True

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

    def _upload_photo (self, url, name):
        tagstr = self.tagWith.replace(","," ")
        ret = self.fapi.upload( api_key=FlickrSink.API_KEY, 
                                auth_token=self.token,
                                filename=url,
                                title=name,
                                is_public="%i" % self.showPublic,
                                tags=tagstr
                                )
        if self.fapi.getRspErrorCode(ret) != 0:
            raise Exceptions.SyncronizeError("Flickr Upload Error: %s" % self.fapi.getPrintableError(ret))
        else:
            #return the photoID
            return ret.photoid[0].elementText
        
    def refresh(self):
        DataProvider.ImageSink.refresh(self)
        self.fapi = FlickrAPI(FlickrSink.API_KEY, FlickrSink.SHARED_SECRET)
        self.token = self.fapi.getToken(self.username, browser="gnome-www-browser -p", perms="write")
        
    def delete(self, LUID):
        #Authenticating with delete permissions does not yet work....
        #
        #if self._get_photo_info(LUID) != None:
        #    ret = self.fapi.photos_delete(
        #                    api_key=FlickrSink.API_KEY,
        #                    photo_id=LUID
        #                    )
        #    if self.fapi.getRspErrorCode(ret) != 0:
        #        logw("Flickr Error Deleting: %s" % self.fapi.getPrintableError(ret))
        #else:
        #    logw("Photo doesnt exist")
        pass

    def configure(self, window):
        """
        Configures the Flickr sink
        """
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "FlickrSinkConfigDialog")
        
        #get a whole bunch of widgets
        tagEntry = tree.get_widget("tag_entry")
        publicCb = tree.get_widget("public_check")
        username = tree.get_widget("username")
        
        #preload the widgets
        tagEntry.set_text(self.tagWith)
        publicCb.set_active(self.showPublic)
        username.set_text(self.username)
        
        dlg = tree.get_widget("FlickrSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            # get the values from the widgets
            self.tagWith = tagEntry.get_text()
            self.showPublic = publicCb.get_active()
            self.username = username.get_text()

            #user must enter their username
            self.set_configured(self.is_configured())

        dlg.destroy()    
       
    def is_configured (self):
        return len (self.username) > 0
        
    def get_configuration(self):
        return {
            "username" : self.username,
            "tagWith" : self.tagWith,
            "showPublic" : self.showPublic
            }

    def get_UID(self):
        return self.token
            
