import os
from os.path import abspath, expanduser
import sys
import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

import traceback
import gnomevfs
import urllib2
from elementtree import ElementTree

import mimetypes

MODULES = {
    "RSSSource" : { "type": "dataprovider" }    
}

class RSSSource(DataProvider.DataSource):

    _name_ = _("RSS Feed")
    _description_ = _("Sync data from RSS enclosures")
    _category_ = DataProvider.CATEGORY_WEB
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "feed-icon"

    PHOTO_TYPES = []
    AUDIO_TYPES = []
    VIDEO_TYPES = []

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        
        #self.feedUrl = "http://www.flickr.com/services/feeds/photos_public.gne?id=44124362632@N01&format=rss_200_enc"
        #self.feedUrl = "http://www.lugradio.org/episodes.ogg.rss"
        self.feedUrl = ""
        self.files = None

        self.allowedTypes = []
        self.limit = 0        
        self.downloadPhotos = True
        self.downloadAudio = True

        mimetypes.init()

        # loop through all mime types and detect common mime types
        for m in mimetypes.types_map.values():
            if m[:6] == "image/":
                self.PHOTO_TYPES.append(m)
            elif m[:6] == "audio/":
                self.AUDIO_TYPES.append(m)
            elif m[:6] == "video/":
                self.VIDEO_TYPES.append(m)

        # why on gods green earth is there an application/ogg :(
        self.AUDIO_TYPES.append("application/ogg")

    def initialize(self):
        return True

    def configure(self, window):
        tree = gtk.glade.XML(conduit.GLADE_FILE, "RSSSourceConfigDialog")
        
        #get a whole bunch of widgets
        url = tree.get_widget("url")
        limitCb = tree.get_widget("limitdownloads")
        limitSb = tree.get_widget("limitnumber")        
        photosCb = tree.get_widget("downloadphotos")
        audioCb = tree.get_widget("downloadaudio")
        
        #preload the widgets
        if self.limit > 0:
            limitCb.set_active(True)
            limitSb.set_value(self.limit)
        else:
            limitCb.set_active(False)
        url.set_text(self.feedUrl)
        photosCb.set_active(self.downloadPhotos)
        audioCb.set_active(self.downloadAudio)
        
        dlg = tree.get_widget("RSSSourceConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            self.feedUrl = url.get_text()
            if limitCb.get_active():
                #Need to cast to a float cause it returns an int
                self.limit = int(limitSb.get_value())
            self.allowedTypes = []
            if photosCb.get_active():
                self.allowedTypes += RSSSource.PHOTO_TYPES
            if audioCb.get_active():
                self.allowedTypes += RSSSource.AUDIO_TYPES
            self.downloadAudio = audioCb.get_active()
            self.downloadPhotos = photosCb.get_active()
            
        dlg.destroy()            
        logging.debug(self.allowedTypes)

    def refresh(self):
        DataProvider.DataSource.refresh(self)

        self.files = []
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
                            if t in self.allowedTypes:
                                if ((url not in allreadyInserted) and ((len(allreadyInserted) < self.limit) or (self.limit == 0))):
                                    allreadyInserted.append(url)
                                    #Make a file
                                    f = File.File(uri=url)
                                    #create the correct extension
                                    # use python built in mimetypes (utilises /etc/mime.types)
                                    #  fix to use pygtk when they are out of api freeze and can fix 349619?
                                    try:
                                        ext = mimetypes.guess_extension(t)
                                    except:
                                        ext = ""
                                    f.force_new_filename(title+ext)
                                    self.files.append(f)
                            else:
                                logging.debug("Enclosure %s is on non-allowed type (%s)" % (title,t))
        except:
            logging.info("Error getting/parsing feed \n%s" % traceback.format_exc())
            raise Exceptions.RefreshError
                            
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return self.files[index]

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)                            
        return len(self.files)

    def finish(self):
        self.files = None

    def get_configuration(self):
        return {
            "feedUrl" : self.feedUrl,
            "allowedTypes" : str(self.allowedTypes),
            "limit" : self.limit,
            "downloadPhotos" : self.downloadPhotos,
            "downloadAudio" : self.downloadAudio
            }
