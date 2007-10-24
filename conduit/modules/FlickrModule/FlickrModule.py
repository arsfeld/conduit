"""
Flickr Uploader.
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

Utils.dataprovider_add_dir_to_path(__file__, "FlickrAPI")
from flickrapi import FlickrAPI

MODULES = {
	"FlickrTwoWay" :          { "type": "dataprovider" }        
}

class FlickrTwoWay(Image.ImageTwoWay):

    _name_ = "Flickr"
    _description_ = "Sync Your Flickr.com Photos"
    _module_type_ = "twoway"
    _icon_ = "flickr"

    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"
    _perms_ = "delete"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.need_configuration(True)
        
        self.fapi = None
        self.token = None
        self.photoSetName = ""
        self.showPublic = True
        self.photoSetId = None
        self.imageSize = "None"

    # Helper methods
    def _get_user_quota(self):
        """
        Returs used,total or -1,-1 on error
        """
        ret = self.fapi.people_getUploadStatus(
                                api_key=FlickrTwoWay.API_KEY, 
                                auth_token=self.token
                                )
        if self.fapi.getRspErrorCode(ret) != 0:
            logd("Flickr people_getUploadStatus Error: %s" % self.fapi.getPrintableError(ret))
            return -1,-1
        else:
            totalkb = ret.user[0].bandwidth[0]["maxkb"]
            usedkb = ret.user[0].bandwidth[0]["usedkb"]
            return int(usedkb),int(totalkb)

    def _get_photo_info(self, photoID):
        info = self.fapi.photos_getInfo(
                                    api_key=FlickrTwoWay.API_KEY,
                                    auth_token=self.token,
                                    photo_id=photoID
                                    )

        if self.fapi.getRspErrorCode(info) != 0:
            logd("Flickr photos_getInfo Error: %s" % self.fapi.getPrintableError(info))
            return None
        else:
            return info

    def _get_raw_photo_url(self, photoInfo):
        photo = photoInfo.photo[0]
        #photo is a dict so we can use pythons string formatting natively with the correct keys
        url = "http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s.jpg" % photo
        return url

    def _upload_photo (self, url, mimeType, name):
        ret = self.fapi.upload( api_key=FlickrTwoWay.API_KEY, 
                                auth_token=self.token,
                                filename=url,
                                title=name,
                                is_public="%i" % self.showPublic
                                )

        if self.fapi.getRspErrorCode(ret) != 0:
            raise Exceptions.SyncronizeError("Flickr Upload Error: %s" % self.fapi.getPrintableError(ret))

        # get the id
        photoId = ret.photoid[0].elementText

        # check if phtotoset exists, create it otherwise add photo to it
        if not self.photoSetId:
            # create one with created photoID if not
            ret = self.fapi.photosets_create(api_key=FlickrTwoWay.API_KEY,
                                             auth_token=self.token,
                                             title=self.photoSetName,
                                             primary_photo_id=photoId)

            if self.fapi.getRspErrorCode(ret) != 0:
                raise Exceptions.SyncronizeError("Flickr failed to create photoset: %s" % self.fapi.getPrintableError(ret))

            self.photoSetId = ret.photoset[0]['id']
        else:
            # add photo to photoset
            ret = self.fapi.photosets_addPhoto(api_key=FlickrTwoWay.API_KEY,
                                               auth_token=self.token,
                                               photoset_id = self.photoSetId,
                                               photo_id = photoId)

            if self.fapi.getRspErrorCode(ret) != 0:
                raise Exceptions.SyncronizeError("Flickr failed to add photo to set: %s" % self.fapi.getPrintableError(ret))

        #return the photoID
        return photoId

    
    def _get_photo_size (self):
        return self.imageSize
        
    # DataProvider methods
    def refresh(self):
        Image.ImageTwoWay.refresh(self)
        self._login()


    def get_all(self):
        # return  photos list is filled, raise error if not
        if not self.photoSetId:
            return []

        ret = self.fapi.photosets_getPhotos(api_key=FlickrTwoWay.API_KEY,
                                            auth_token=self.token,
                                            photoset_id=self.photoSetId)

        if self.fapi.getRspErrorCode (ret) != 0:
            raise Exceptions.SyncronizeError("Flickr failed to get photos: %s" % self.fapi.getPrintableError(ret))

        photoList = []

        for photo in ret.photoset[0].photo:
            photoList.append(photo['id'])

        return photoList


    def get (self, LUID):
        # get photo info
        photoInfo = self._get_photo_info(LUID)
        # get url
        url = self._get_raw_photo_url (photoInfo)
        # get the title
        title = str(photoInfo.photo[0].title[0].elementText)

        # create the file
        f = File.File (URI=url)
        f.set_open_URI(url)

        # try to rename if a title is available
        # FIXME: this is far from optimal, also there should be 
        # a way to get out the originals
        if title:
            if not title.endswith('jpg'):
                title = title + '.jpg'
            f.force_new_filename(title)

        f.set_UID(LUID)

        return f

    def _login(self):
        """
        Get ourselves a token we can use to perform all calls
        """
        self.fapi = FlickrAPI(FlickrTwoWay.API_KEY, FlickrTwoWay.SHARED_SECRET)
       
        # can we get a cached token? 
        self.token = self.fapi.getCachedToken(self.username, perms=self._perms_)

        # create a new one if not
        if self.token == None:
            # get frob and open it
            self.frob = self.fapi.getFrob()
            url = self.fapi.getAuthURL(self._perms_, self.frob)
            # wait for user to login
            Web.LoginMagic("Log into Flickr", url, login_funtion=self._try_login)

        # try to get the photoSetId
        ret = self.fapi.photosets_getList(api_key=FlickrTwoWay.API_KEY,
                                          auth_token=self.token)

        if self.fapi.getRspErrorCode(ret) != 0:
            raise Exceptions.RefreshError("Flickr Refresh Error: %s" % self.fapi.getPrintableError(ret))

        if not hasattr(ret.photosets[0], 'photoset'):
            return

        # look up the photo set
        for set in ret.photosets[0].photoset:
            if set.title[0].elementText == self.photoSetName:
                self.photoSetId = set['id']      
                                                      

    def _try_login(self):
        """
        This function is used by the login tester, we try to get a token,
        but return None if it does not succeed so the login tester can keep trying
        """
        try:
            self.token = self.fapi.getAuthToken(self.username, self.frob)
            self.frob = None
            return self.token
        except:
            return None

    def delete(self, LUID):
        if self._get_photo_info(LUID) != None:
            ret = self.fapi.photos_delete(
                            api_key=FlickrTwoWay.API_KEY,
                            auth_token=self.token,
                            photo_id=LUID
                            )
            if self.fapi.getRspErrorCode(ret) != 0:
                logw("Flickr Error Deleting: %s" % self.fapi.getPrintableError(ret))
            else:
                logd("Successfully deleted photo [%s]" % LUID)
        else:
            logw("Photo doesnt exist")

    def configure(self, window):
        """
        Configures the Flickr sink
        """
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "FlickrTwoWayConfigDialog")
        
        #get a whole bunch of widgets
        photoSetEntry = tree.get_widget("photoset_entry")
        publicCb = tree.get_widget("public_check")
        username = tree.get_widget("username")

        resizecombobox = tree.get_widget("resizecombobox")
        self._resize_combobox_build(resizecombobox, self.imageSize)
        
        #preload the widgets
        photoSetEntry.set_text(self.photoSetName)
        publicCb.set_active(self.showPublic)
        username.set_text(self.username)
        
        dlg = tree.get_widget("FlickrTwoWayConfigDialog")
        response = Utils.run_dialog(dlg, window)

        if response == True:
            # get the values from the widgets
            self.photoSetName = photoSetEntry.get_text()
            self.showPublic = publicCb.get_active()
            self.username = username.get_text()
            self.imageSize = self._resize_combobox_get_active(resizecombobox)

            #user must enter their username
            self.set_configured(self.is_configured())

        dlg.destroy()    
       
    def is_configured (self):
        return len (self.username) > 0
        
    def get_configuration(self):
        return {
            "imageSize" : self.imageSize,
            "username" : self.username,
            "photoSetName" : self.photoSetName,
            "showPublic" : self.showPublic
            }

    def get_UID(self):
        return self.token
            
