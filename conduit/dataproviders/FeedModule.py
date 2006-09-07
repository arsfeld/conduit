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

MODULES = {
	"RSSSource" : {
		"name": _("RSS Source"),
		"description": _("Sync data from RSS enclosures"),
		"type": "source",
		"category": DataProvider.CATEGORY_WEB,
		"in_type": "file",
		"out_type": "file"
	}	
}

class RSSSource(DataProvider.DataSource):
    MIME_EXT_DICT = {
                    "image/jpeg" : ".jpg",
                    "audio/mpeg" : ".mp3",
                    "application/ogg" : ".ogg"
                    }
    PHOTO_TYPES = ["image/jpeg"]
    AUDIO_TYPES = ["audio/mpeg", "application/ogg"]
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("RSS Source"), _("Sync data from RSS enclosures"))
        self.icon_name = "feed-icon"
        
        #self.feedUrl = "http://www.flickr.com/services/feeds/photos_public.gne?id=44124362632@N01&format=rss_200_enc"
        #self.feedUrl = "http://www.lugradio.org/episodes.ogg.rss"
        self.feedUrl = ""
        self.files = []

        self.allowedTypes = []
        self.limit = 0        
        self.downloadPhotos = True
        self.downloadAudio = True

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
                                    f = File.File(url)
                                    #create the correct extension
                                    #FIXME:hack because no way to get extensions for
                                    #mimetype in pygtk. See 349619
                                    try:
                                        ext = RSSSource.MIME_EXT_DICT[t]
                                    except:
                                        ext = ""
                                    f.force_new_filename(title+ext)
                                    self.files.append(f)
                            else:
                                logging.debug("Enclosure %s is on non-allowed type (%s)" % (title,t))
        except:
            logging.info("Error getting/parsing feed \n%s" % traceback.format_exc())
            raise Exceptions.RefreshError
                            
    def get(self):
        for f in self.files:
            yield f                            

    def get_configuration(self):
        return {
            "feedUrl" : self.feedUrl,
            "allowedTypes" : str(self.allowedTypes),
            "limit" : self.limit,
            "downloadPhotos" : self.downloadPhotos,
            "downloadAudio" : self.downloadAudio
            }
