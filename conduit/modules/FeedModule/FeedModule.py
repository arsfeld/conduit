try:
    from elementtree import ElementTree
except:
    from xml.etree import ElementTree

import mimetypes
import traceback

import urllib2
import os
from os.path import abspath, expanduser
import sys
from gettext import gettext as _
import logging
log = logging.getLogger("modules.Feed")

import conduit
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

MODULES = {
    "RSSSource" : { "type": "dataprovider" }    
}

class RSSSource(DataProvider.DataSource):

    _name_ = _("RSS Feed")
    _description_ = _("Sync data from RSS enclosures")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _in_type_ = ""
    _out_type_ = "file"
    _icon_ = "feed"

    PHOTO_TYPES = []
    AUDIO_TYPES = []
    VIDEO_TYPES = []

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        
        self.feedUrl = ""
        self.files = {}

        self.limit = 0        
        self.downloadPhotos = True
        self.downloadAudio = True
        self.downloadVideo = True

        mimetypes.init()

        # loop through all mime types and detect common mime types
        for m in mimetypes.types_map.values():
            if m[:6] == "image/":
                RSSSource.PHOTO_TYPES.append(m)
            elif m[:6] == "audio/":
                RSSSource.AUDIO_TYPES.append(m)
            elif m[:6] == "video/":
                RSSSource.VIDEO_TYPES.append(m)

        # why on gods green earth is there an application/ogg :(
        self.AUDIO_TYPES.append("application/ogg")

    def initialize(self):
        return True

    def configure(self, window):
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"RSSSourceConfigDialog"
						)
        
        #get a whole bunch of widgets
        url = tree.get_widget("url")
        limitCb = tree.get_widget("limitdownloads")
        limitSb = tree.get_widget("limitnumber")        
        photosCb = tree.get_widget("downloadphotos")
        audioCb = tree.get_widget("downloadaudio")
        videoCb = tree.get_widget("downloadvideo")
        
        #preload the widgets
        if self.limit > 0:
            limitCb.set_active(True)
            limitSb.set_value(self.limit)
        else:
            limitCb.set_active(False)
        url.set_text(self.feedUrl)
        photosCb.set_active(self.downloadPhotos)
        audioCb.set_active(self.downloadAudio)
        videoCb.set_active(self.downloadVideo)
                
        dlg = tree.get_widget("RSSSourceConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.feedUrl = url.get_text()
            if limitCb.get_active():
                #Need to cast to a float cause it returns an int
                self.limit = int(limitSb.get_value())
            self.downloadPhotos = photosCb.get_active()
            self.downloadAudio = audioCb.get_active()
            self.downloadVideo = videoCb.get_active()
            
        dlg.destroy()            

    def refresh(self):
        DataProvider.DataSource.refresh(self)

        #Add allowed mimetypes to filter
        allowedTypes = []
        if self.downloadPhotos:
            allowedTypes += RSSSource.PHOTO_TYPES
        if self.downloadAudio:
            allowedTypes += RSSSource.AUDIO_TYPES
        if self.downloadVideo:
            allowedTypes += RSSSource.VIDEO_TYPES

        self.files = {}
        try:
            url_info = urllib2.urlopen(self.feedUrl)
            if (url_info):
                doc = ElementTree.parse(url_info).getroot()
                #FIXME: My XML element tree foo is not that good. It seems to reprocess
                #each item tag for each namespace???. This means i get n+1 copies
                #of each enclosure. 1 from the bland doc, and one from each other namespace.
                allreadyInserted = []
                for item in doc.getiterator("item"):
                    url = None
                    t = None
                    title = None
                    for c in item.getchildren():
                        if c.tag == "enclosure":
                            url = c.get("url")
                            t = c.get("type")
                        if c.tag == "title":
                            title = c.text
                            
                        #Check if we have all the info
                        if url and t and title:
                            log.debug("Got enclosure %s %s (%s)" % (title,url,t))
                            if t in allowedTypes:
                                if ((url not in allreadyInserted) and ((len(allreadyInserted) < self.limit) or (self.limit == 0))):
                                    allreadyInserted.append(url)
                                    self.files[url] = (title,t)
                            else:
                                log.debug("Enclosure %s is on non-allowed type (%s)" % (title,t))
        except:
            log.info("Error getting/parsing feed \n%s" % traceback.format_exc())
            raise Exceptions.RefreshError

    def get_all(self):
        DataProvider.DataSource.get_all(self)                            
        return self.files.keys()
            
    def get(self, url):
        DataProvider.DataSource.get(self, url)
        #Make a file
        f = File.File(URI=url)
        f.set_UID(url)
        f.set_open_URI(url)
        
        #create the correct extension and filename
        try:
            title,t = self.files[url]
            ext = mimetypes.guess_extension(t)
            f.force_new_filename(title)
            f.force_new_file_extension(ext)
        except:
            log.warn("Error setting filename\n%s" % traceback.format_exc())

        return f

    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.files = {}

    def get_configuration(self):
        return {
            "feedUrl" : self.feedUrl,
            "limit" : self.limit,
            "downloadPhotos" : self.downloadPhotos,
            "downloadAudio" : self.downloadAudio,
            "downloadVideo" : self.downloadVideo
            }

    def get_UID(self):
        return self.feedUrl

