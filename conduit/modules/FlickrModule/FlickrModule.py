"""
Flickr Uploader.
"""
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

if flickrapi.__version__ == "1.1":
    MODULES = {
    	"FlickrTwoWay" :          { "type": "dataprovider" }        
    }
    log.info("Module Information: %s" % Utils.get_module_information(flickrapi, "__version__"))
    #turn of debugging in the library
    flickrapi.set_log_level(logging.NOTSET)
else:
    MODULES = {}
    log.info("Flickr support disabled")
    
class MyFlickrAPI(flickrapi.FlickrAPI):
    """
    Wraps the FlickrAPI in order to override validate_frob to launch the conduit
    web browser.
    """
    #Note that the order, and assignment of values to self.myFrob
    #and self.myToken is important - if done incorrectly then FlickrAPI.__getattr__
    #returns a handler function for them, and not the actual value requested
    def __init__(self, api_key, secret, username):
        flickrapi.FlickrAPI.__init__(self, 
                    api_key=api_key, 
                    secret=secret, 
                    username=username,
                    token=None,
                    format='xmlnode',
                    store_token=True,
                    cache=False
                    )
        self.myFrob = None
        self.myToken = None
                        
    def validate_frob(self, frob, perms):
        self.myFrob = frob
        Web.LoginMagic("Log into Flickr", self.auth_url(perms, frob), login_function=self.try_login)    
            
    def try_login(self):
        try:
            self.myToken = self.get_token(self.myFrob)
            return True
        except flickrapi.FlickrError:
            return False
            
    def login(self):
        token, frob = self.get_token_part_one(perms='delete')
        if token:
            log.debug("Got token from cache")
            return token
        else:
            log.debug("Got token from web")
            return self.myToken

class FlickrTwoWay(Image.ImageTwoWay):

    _name_ = _("Flickr")
    _description_ = _("Synchronize your Flickr.com photos")
    _module_type_ = "twoway"
    _icon_ = "flickr"
    _configurable_ = True

    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.fapi = None
        self.token = None
        self.logged_in = False
        self.photoSetId = None
        self.update_configuration(
            imageSize = "None",
            username = ("", self._set_username),
            photoSetName = "",
            showPublic = True
        )

    # Helper methods
    def _get_user_quota(self):
        """
        Returs used,total or -1,-1 on error
        """
        try:
            ret = self.fapi.people_getUploadStatus()
            totalkb =   int(ret.user[0].bandwidth[0]["maxkb"])
            usedkb =    int(ret.user[0].bandwidth[0]["usedkb"])
            p = (float(usedkb)/totalkb)*100.0
            return usedkb,totalkb,p
        except flickrapi.FlickrError, e:
            log.debug("Error getting quota: %s" % e)
            return -1,-1,100

    def _get_photo_info(self, photoID):
        try:
            return self.fapi.photos_getInfo(photo_id=photoID)
        except flickrapi.FlickrError, e:
            log.debug("Error getting photo info: %s" % e)
            return None

    def _get_raw_photo_url(self, photoInfo):
        photo = photoInfo.photo[0]
        #photo is a dict so we can use pythons string formatting natively with the correct keys
        url = "http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s.jpg" % photo
        return url

    def _upload_photo (self, uploadInfo):
        try:
            ret = self.fapi.upload( 
                                filename=uploadInfo.url,
                                title=uploadInfo.name,
                                description=uploadInfo.caption,
                                is_public="%i" % self.showPublic,
                                tags=' '.join(tag.replace(' ', '_') for tag in uploadInfo.tags))
        except flickrapi.FlickrError, e:
            raise Exceptions.SyncronizeError("Flickr Upload Error: %s" % e)

        # get the id
        photoId = ret.photoid[0].text

        # check if phtotoset exists, if not create it
        firstPhoto = False
        if not self.photoSetId:
            self.photoSetId = self._create_photoset(photoId)
            # first photo shouldn't be added to photoset as Flickrs does it for us
            firstPhoto = True

        # add the photo to the photoset
        if self.photoSetId and not firstPhoto:
            try:
                ret = self.fapi.photosets_addPhoto(
                                    photoset_id = self.photoSetId,
                                    photo_id = photoId)
            except flickrapi.FlickrError, e:
                log.warn("Flickr failed to add %s to set: %s" % (photoId,e))

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
        try:
            ret = self.fapi.photosets_create(
                                    title=self.photoSetName,
                                    primary_photo_id=primaryPhotoId)
            return ret.photoset[0]['id']
        except flickrapi.FlickrError, e:
            log.warn("Flickr failed to create photoset %s: %s" % (self.photoSetName,e))
            return None
                
    def _get_photoset(self):
        for name, photoSetId in self._get_photosets():
            if name == self.photoSetName:
                log.debug("Found album %s" % self.photoSetName)
                self.photoSetId = photoSetId
                
    def _get_photosets(self):
        photosets = []
        try:
            ret = self.fapi.photosets_getList()  
            if hasattr(ret.photosets[0], 'photoset'):
                for pset in ret.photosets[0].photoset:
                    photosets.append(
                                (pset.title[0].text,        #photoset name
                                pset['id']))                #photoset id
        except flickrapi.FlickrError, e:
            log.debug("Failed to get photosets: %s" % e)

        return photosets        
        
    def _get_photos(self):
        if not self.photoSetId:
            return []

        photoList = []
        try:
            ret = self.fapi.photosets_getPhotos(photoset_id=self.photoSetId)
            for photo in ret.photoset[0].photo:
                photoList.append(photo['id'])
        except flickrapi.FlickrError, e:
            log.warn("Flickr failed to get photos: %s" % e)

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
        title = str(photoInfo.photo[0].title[0].text)
        # get tags
        tagsNode = photoInfo.photo[0].tags[0]
        # get caption
        caption = photoInfo.photo[0].description[0].text
        
        if hasattr(tagsNode, 'tag'):
            tags = tuple(tag.text for tag in tagsNode.tag)
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
            try:
                ret = self.fapi.photos_delete(photo_id=LUID)
                log.debug("Successfully deleted photo: %s" % LUID)
            except flickrapi.FlickrError, e:
                log.warn("Error deleting %s: %s" % (LUID,e))
        else:
            log.warn("Error deleting %s: doesnt exist" % LUID)

    def config_setup(self, config):
              
        def _login_finished(*args):
            try:
                if self.logged_in:
                    status_label.value = 'Loading album list...'
                    try:
                        #FIXME: Blocks and brings the whole UI with it.
                        photosets = self._get_photosets()
                    except:
                        status_label.value = '<span foreground="red">Failed to connect.</span>'
                    else:
                        photoset_config.choices = [name for name, photoSetId in photosets]
                        status_label.value = 'Album names loaded.'
                else:
                    #FIXME: The red color is pretty eye-candy, but might be too
                    #distracting and unnecessary, we should re-evaluate it's 
                    #usefulness
                    status_label.value = '<span foreground="red">Failed to login.</span>'
            finally:
                load_photosets_config.enabled = True
                
        def _load_photosets(button):
            load_photosets_config.enabled = False
            #FIXME: This applies the username value before OK/Apply is clicked, 
            #we should do a better job
            username_config.apply()
            status_label.value = 'Logging in, please wait...'
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                self, _login_finished, self._login)

        config.add_section('Account details')
        username_config = config.add_item('Username', 'text',
            config_name = 'username',
        )
        username_config.connect('value-changed',
            lambda item, initial, value: load_photosets_config.set_enabled(bool(value)))
        status_label = config.add_item('Status', 'label',
            initial_value = self.status,
            use_markup = True,
        )
        config.add_section('Saved photo settings')
        load_photosets_config = config.add_item("Load photosets", "button",
            initial_value = _load_photosets
        )        
        photoset_config = config.add_item('Photoset name', 'combotext',
            config_name = 'photoSetName',
            choices = [],
        )
        config.add_item("Resize photos", "combo",
            choices = [("None", "Do not resize"), "640x480", "800x600", "1024x768"],
            config_name = "imageSize"
        )
        config.add_item('Photos are public', 'check',
            config_name = 'showPublic'
        )
       
    def is_configured (self, isSource, isTwoWay):
        return len(self.username) > 0 and len(self.photoSetName) > 0
        
    def get_UID(self):
        return self.token
            
