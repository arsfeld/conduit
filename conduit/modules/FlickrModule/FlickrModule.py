"""
Flickr Uploader.
"""
import os, sys
import traceback
import md5
import logging
log = logging.getLogger("modules.Flickr")

import conduit
import conduit.utils as Utils
import conduit.Web as Web
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
import conduit.datatypes.Photo as Photo
from conduit.datatypes import Rid

from gettext import gettext as _

#We have to use our own flickrapi until the following is applied
#http://sourceforge.net/tracker/index.php?func=detail&aid=1874067&group_id=203043&atid=984009
Utils.dataprovider_add_dir_to_path(__file__)
import flickrapi

if flickrapi.__version__.endswith("CONDUIT"):
    MODULES = {
    	"FlickrTwoWay" :          { "type": "dataprovider" }        
    }
    log.info("Module Information: %s" % Utils.get_module_information(flickrapi, "__version__"))
else:
    MODULES = {}
    log.info("Flickr support disabled")
    
class MyFlickrAPI(flickrapi.FlickrAPI):
    def __init__(self, apiKey, secret, username):
            flickrapi.FlickrAPI.__init__(self, 
                        apiKey, 
                        secret, 
                        fail_on_error=True, 
                        username=username
                        )
                        
    def validateFrob(self, frob, perms):
        self.frob = frob
        encoded = self.encode_and_sign({
                    "api_key": self.api_key,
                    "frob": frob,
                    "perms": perms})
        auth_url = "http://%s%s?%s" % (flickrapi.FlickrAPI.flickrHost, flickrapi.FlickrAPI.flickrAuthForm, encoded)        
        Web.LoginMagic("Log into Flickr", auth_url, login_function=self.try_login)
        
    def try_login(self):
        try:
            self.getTokenPartTwo((self.token, self.frob))
            return True
        except flickrapi.FlickrError:
            return False
            
    def login(self):
        token, frob = self.getTokenPartOne(perms='delete')
        return token

class FlickrTwoWay(Image.ImageTwoWay):

    _name_ = _("Flickr")
    _description_ = _("Sync your Flickr.com photos")
    _module_type_ = "twoway"
    _icon_ = "flickr"

    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"
    _perms_ = "delete"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.fapi = None
        self.token = None
        self.username = ""
        self.logged_in = False
        self.photoSetName = ""
        self.showPublic = True
        self.photoSetId = None
        self.imageSize = "None"

    # Helper methods
    def _get_user_quota(self):
        """
        Returs used,total or -1,-1 on error
        """
        ret = self.fapi.people_getUploadStatus()
        if self.fapi.getRspErrorCode(ret) != 0:
            log.debug("Flickr people_getUploadStatus Error: %s" % self.fapi.getPrintableError(ret))
            return -1,-1,100
        else:
            totalkb =   int(ret.user[0].bandwidth[0]["maxkb"])
            usedkb =    int(ret.user[0].bandwidth[0]["usedkb"])
            p = (float(usedkb)/totalkb)*100.0
            return usedkb,totalkb,p

    def _get_photo_info(self, photoID):
        info = self.fapi.photos_getInfo(photo_id=photoID)

        if self.fapi.getRspErrorCode(info) != 0:
            log.debug("Flickr photos_getInfo Error: %s" % self.fapi.getPrintableError(info))
            return None
        else:
            return info

    def _get_raw_photo_url(self, photoInfo):
        photo = photoInfo.photo[0]
        #photo is a dict so we can use pythons string formatting natively with the correct keys
        url = "http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s.jpg" % photo
        return url

    def _upload_photo (self, uploadInfo):
        ret = self.fapi.upload( 
                            filename=uploadInfo.url,
                            title=uploadInfo.name,
                            description=uploadInfo.caption,
                            is_public="%i" % self.showPublic,
                            tags=' '.join(tag.replace(' ', '_') for tag in uploadInfo.tags))

        if self.fapi.getRspErrorCode(ret) != 0:
            raise Exceptions.SyncronizeError("Flickr Upload Error: %s" % self.fapi.getPrintableError(ret))

        # get the id
        photoId = ret.photoid[0].elementText

        # check if phtotoset exists, if not create it
        if not self.photoSetId:
            self.photoSetId = self._create_photoset(photoId)
        # add the photo to the photoset
        if self.photoSetId:
            ret = self.fapi.photosets_addPhoto(
                                photoset_id = self.photoSetId,
                                photo_id = photoId)
            if self.fapi.getRspErrorCode(ret) != 0:
                log.warn("Flickr failed to add photo to set: %s" % self.fapi.getPrintableError(ret))

        #return the photoID
        return Rid(uid=photoId)

    def _get_photo_size (self):
        return self.imageSize

    def _set_username(self, username):
        if self.username != username:
            self.username = username
            self.logged_in = False        

    def _login(self):
        #only log in if we need to
        if not self.logged_in:
            self.fapi = MyFlickrAPI(FlickrTwoWay.API_KEY, FlickrTwoWay.SHARED_SECRET, self.username)
            self.token = self.fapi.login()
            self.logged_in = True
            
    def _create_photoset(self, primaryPhotoId):
        #create one with created photoID if not
        ret = self.fapi.photosets_create(
                                title=self.photoSetName,
                                primary_photo_id=primaryPhotoId)

        photoSetId = None
        if self.fapi.getRspErrorCode(ret) != 0:
            log.warn("Flickr failed to create photoset: %s" % self.fapi.getPrintableError(ret))
        else:
            photoSetId = ret.photoset[0]['id']
        return photoSetId
                
    def _get_photoset(self):
        for name, photoSetId in self._get_photosets():
            if name == self.photoSetName:
                log.debug("Found album %s" % self.photoSetName)
                self.photoSetId = photoSetId
                
    def _get_photosets(self):
        ret = self.fapi.photosets_getList()  
        if self.fapi.getRspErrorCode(ret) != 0:
            log.warn("Flickr Refresh Error: %s" % self.fapi.getPrintableError(ret))
            return []

        photosets = []
        if hasattr(ret.photosets[0], 'photoset'):
            for pset in ret.photosets[0].photoset:
                photosets.append(
                            (pset.title[0].elementText, #photoset name
                            pset['id']))                #photoset id

        return photosets
        
    def _get_photos(self):
        if not self.photoSetId:
            return []

        photoList = []
        ret = self.fapi.photosets_getPhotos(photoset_id=self.photoSetId)
        if self.fapi.getRspErrorCode(ret) != 0:
            log.warn("Flickr failed to get photos: %s" % self.fapi.getPrintableError(ret))
        else:            
            for photo in ret.photoset[0].photo:
                photoList.append(photo['id'])
        return photoList
        
    # DataProvider methods
    def refresh(self):
        Image.ImageTwoWay.refresh(self)
        self._login()
        self._get_photoset()            
        used,tot,percent = self._get_user_quota()
        log.debug("Used %2.1f%% of monthly badwidth quota (%skb/%skb)" % (percent,used,tot))

    def get_all(self):
        return self._get_photos()

    def get (self, LUID):
        # get photo info
        photoInfo = self._get_photo_info(LUID)
        # get url
        url = self._get_raw_photo_url (photoInfo)
        # get the title
        title = str(photoInfo.photo[0].title[0].elementText)
        # get tags
        tagsNode = photoInfo.photo[0].tags[0]
        # get caption
        caption = photoInfo.photo[0].description[0].elementText
        
        if hasattr(tagsNode, 'tag'):
            tags = tuple(tag.elementText for tag in tagsNode.tag)
        else:
            tags = ()

        # create the file
        f = Photo.Photo (URI=url)
        f.set_open_URI(url)
        f.set_caption(caption)

        # try to rename if a title is available
        # FIXME: this is far from optimal, also there should be 
        # a way to get out the originals
        if title:
            if not title.endswith('jpg'):
                title = title + '.jpg'
            f.force_new_filename(title)

        f.set_UID(LUID)

        # set the tags
        f.set_tags (tags)

        return f

    def delete(self, LUID):
        if self._get_photo_info(LUID) != None:
            ret = self.fapi.photos_delete(photo_id=LUID)
            if self.fapi.getRspErrorCode(ret) != 0:
                log.warn("Flickr Error Deleting: %s" % self.fapi.getPrintableError(ret))
            else:
                log.debug("Successfully deleted photo [%s]" % LUID)
        else:
            log.warn("Photo doesnt exist")

    def configure(self, window):
        """
        Configures the Flickr sink
        """
        import gobject
        import gtk
        def on_login_finish(*args):
            if self.logged_in:
                build_photoset_model()
            Utils.dialog_reset_cursor(dlg)
                
        def on_response(sender, responseID):
            if responseID == gtk.RESPONSE_OK:
                self._set_username(username.get_text())
                self.photoSetName = photosetCombo.get_active_text()
                self.showPublic = publicCb.get_active()
                self.imageSize = self._resize_combobox_get_active(resizecombobox)
        
        def load_click(button, window, usernameEntry):
            self._set_username(usernameEntry.get_text())
            Utils.dialog_set_busy_cursor(dlg)
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                                            self,
                                            on_login_finish,
                                            self._login)            

        def username_changed(entry, load_button):
            load_button.set_sensitive (len(entry.get_text()) > 0)

        def build_photoset_model():
            photoset_store.clear()
            photoset_count = 0
            photoset_iter = None
            for name, photoSetId in self._get_photosets():       
                iter = photoset_store.append((name,))
                if name == self.photoSetName:
                    photoset_iter = iter
                photoset_count += 1

            if photoset_iter:
                photosetCombo.set_active_iter(photoset_iter)
            elif self.photoSetName:
                photosetCombo.child.set_text(self.photoSetName)
            elif photoset_count:
                photosetCombo.set_active(0)
 
        #get a whole bunch of widgets
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade", 
                        "FlickrTwoWayConfigDialog")
        photosetCombo = tree.get_widget("photoset_combo")
        publicCb = tree.get_widget("public_check")
        username = tree.get_widget("username")
        load_button = tree.get_widget('load_button')
        ok_button = tree.get_widget('ok_button')
        dlg = tree.get_widget("FlickrTwoWayConfigDialog")

        resizecombobox = tree.get_widget("resizecombobox")
        self._resize_combobox_build(resizecombobox, self.imageSize)

        #signals
        load_button.connect('clicked', load_click, window, username)
        username.connect('changed', username_changed, load_button)
        
        #preload the widgets
        publicCb.set_active(self.showPublic)
        username.set_text(self.username)

        #setup photoset combo
        photoset_store = gtk.ListStore (gobject.TYPE_STRING)
        photosetCombo.set_model(photoset_store)
        cell = gtk.CellRendererText()
        photosetCombo.pack_start(cell, True)
        photosetCombo.set_text_column(0)

        #disable photoset lookup if no username entered
        enabled = len(self.username) > 0
        load_button.set_sensitive(enabled)
        
        # run dialog 
        Utils.run_dialog_non_blocking(dlg, on_response, window)
       
    def is_configured (self, isSource, isTwoWay):
        return len(self.username) > 0 and len(self.photoSetName) > 0
        
    def get_configuration(self):
        return {
            "imageSize" : self.imageSize,
            "username" : self.username,
            "photoSetName" : self.photoSetName,
            "showPublic" : self.showPublic
            }

    def get_UID(self):
        return self.token
            
