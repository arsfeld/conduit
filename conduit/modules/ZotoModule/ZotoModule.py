# -*- coding: utf-8 -*-

"""
Zoto Data Sink
"""
import logging
log = logging.getLogger("modules.Zoto")

import conduit
import conduit.utils as Utils
from conduit.datatypes import Rid
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
import conduit.datatypes.Photo as Photo

from gettext import gettext as _

import xmlrpclib
import md5
import os

MODULES = {
        "ZotoSink" : {"type" : "dataprovider"},
}

class MyZotoAPI:
    def __init__(self, username, password):
        self.zapiKey = '588c270052e2157c4fa7e10b80b2c580'
        self.username = username
        self.password = md5.md5(password).hexdigest() # password
        
        self.zotoAuth = {'username': self.username, 'password': self.password}
        self.server = xmlrpclib.Server('http://www.zoto.com/RPC2/')

    def delete_photo(self, photoId):
        self.server.images.delete(self.zapiKey, self.zotoAuth, photoId)

    def create_album(self, albumName):
        """
        Creates a new album. Returns the id for it
        """
        return self.server.albums.create_album(self.zapiKey, self.zotoAuth,
                                               {'title':albumName, 'description': albumName})[1]

    def get_albums(self):
        albums = {}
        for al in self.server.sets.get_albums(self.zapiKey, self.zotoAuth, self.username, {}, 9999, 0)[1]:
            albums[al['title']] = al['album_id']

        return albums

    def get_photos_album(self, albumId):
        """
        Gets all the photos from album albumId.
        Returns a dict like this <photoId> : <Photo>
        """

        photosDict = {}
        photos = self.server.albums.get_images(self.zapiKey, self.zotoAuth, albumId, {}, 9999, 0)[1]

        for zf in photos:
            photoId = zf['media_id']
            # The extension is jpg even if in the original name was JPG or jpeg
            photoUrl = 'http://www.zoto.com/%s/img/original/%s.jpg' % (self.username, photoId)

            # construct photo
            f = Photo.Photo(URI=photoUrl)
            f.set_open_URI(photoUrl)
            f.set_UID(photoId)
            f.set_caption (zf['description'])
            f.force_new_filename(zf['title'])
            f.set_tags(self.get_photo_tags(photoId))

            # add to dict
            photosDict[photoId] = f

        return photosDict        

    def add_to_album(self, uploadInfo, albumId):
        """
        Adds a photo to the album. 
        """
        f = open(uploadInfo.url,'r')
        buf=f.read()                
        f.close()
        fotoId= md5.md5(buf).hexdigest()

        if not uploadInfo.caption:
            uploadInfo.caption=''

        self.server.images.add(self.zapiKey, self.zotoAuth, uploadInfo.name,
                               uploadInfo.name, uploadInfo.caption, xmlrpclib.Binary(buf))
        self.server.albums.multi_add_image(self.zapiKey, self.zotoAuth,
                                           albumId, [fotoId])
        tags = []
        for tag in uploadInfo.tags:
            tags.append(tag)

        if len(tags) > 0:
            self.server.tags.multi_tag_image(self.zapiKey, self.zotoAuth,
                                             self.username, [fotoId], tags)

        return fotoId

    def delete_from_album(self, photoId, albumId):
        self.server.albums.multi_del_image(self.zapiKey, self.zotoAuth,
                                           albumId, [photoId])

    def get_photo_tags(self, photoId):
        """
        Returns a list with the photo's tags
        """
        tags=[]
        for t in self.server.tags.get_image_tags(self.zapiKey, self.zotoAuth,
                                                 self.username, photoId, 'owner'):
            tags.append(t['tag_name'])    

        return tags

class ZotoSink(Image.ImageTwoWay):
    _name_ = _("Zoto")
    _description_ = _("Sync your Zoto photos")
    _module_type_ = "twoway"
    _icon_ = "zoto"
    _configurable_ = True
    
    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.username = ""
        self.password = ""
        self.albumName = ""
        self.albumId = None
        self.sphotos = None
        self.zapi = None
        self.albums = None

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo.get_open_URI()

    def _get_photo_info(self, id):
        if self.sphotos.has_key(id):
                return self.sphotos[id]
        else:
                return None
        
    def _get_photo_formats(self):
        return ("image/jpeg", )
        
    def refresh(self):            
        Image.ImageTwoWay.refresh(self)

        try:
            self.zapi = MyZotoAPI(self.username, self.password)
            albums = self.zapi.get_albums()
            if not albums.has_key(self.albumName):
                self.albumId = self.zapi.create_album(self.albumName)
            else:
                self.albumId = albums[self.albumName]
                
            self.sphotos = self.zapi.get_photos_album(self.albumId)
        except xmlrpclib.Fault, e:
            log.debug("Error refreshing: %s" % e.faultString)
            raise Exceptions.RefreshError (e.faultString)
        
    def get_all(self):
        return self.sphotos.keys()

    def get(self, LUID):
        return self.sphotos[LUID]

    def delete(self, LUID):
        """
        Delete a photo by ID
        """
        if not self.sphotos.has_key(LUID):
            log.warn("Photo does not exist")
            return

        try:
            self.zapi.delete_from_album(LUID, self.albumId)
            del self.sphotos[LUID]
        except xmlrpclib.Fault, e:
            raise Exceptions.SyncronizeError("Zoto Delete Error: " +  e.faultString)

    def _upload_photo(self, uploadInfo):
        """
        Upload to album
        """
        try:
            fotoId = self.zapi.add_to_album(uploadInfo, self.albumId)
        except Exception, e:
            raise Exceptions.SyncronizeError("Zoto Upload Error.")
        
        return Rid(uid=fotoId)

    def configure(self, window):
        """
        Configures the ZotoSink
        """
        widget = Utils.dataprovider_glade_get_widget(
                __file__,
                "zoto.glade",
                "ZotoSinkConfigDialog")
                
        # Get configuration widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        album = widget.get_widget("album")
                
        # Load the widgets with presets
        username.set_text(self.username)
        password.set_text(self.password)
        album.set_text(self.albumName)
                
        dlg = widget.get_widget("ZotoSinkConfigDialog")
        
        response = Utils.run_dialog(dlg, window)
                
        if response == True:
            self.username = username.get_text()
            self.password = password.get_text()
            self.albumName = album.get_text()
                
        dlg.destroy()
        
    def get_configuration(self):
        return {
                "username" : self.username, 
                "password" : self.password, 
                "albumName" : self.albumName
                }
        
    def is_configured(self, isSource, isTwoWay):
        if len(self.username) < 1:
            return False
        if len(self.password) < 1:
            return False
        if len(self.albumName) < 1:
            return False

        return True
        
    def get_UID(self):
        return self.username+":"+self.albumName
