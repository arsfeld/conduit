import os
from os.path import abspath, expanduser
import sys
import gtk
import re
from gettext import gettext as _


import conduit
import logging
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

import traceback
import gnomevfs
import urllib2

try:
    from elementtree import ElementTree
except:
    from xml.etree import ElementTree

import mimetypes

MODULES = {
    "YouTubeSource" : { "type": "dataprovider" }    
}

class YouTubeSource(DataProvider.DataSource):

    _name_ = _("YouTube")
    _description_ = _("Sync data from YouTube")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _in_type_ = ""
    _out_type_ = "file"
    _icon_ = "youtube"

    #feeds_url
    _const_feed_most_viewed_ = "http://gdata.youtube.com/feeds/standardfeeds/most_viewed?time=today"
    _const_feed_top_rated_ = "http://gdata.youtube.com/feeds/standardfeeds/top_rated?time=today"
    _const_feed_upload_by_ = "http://gdata.youtube.com/feeds/videos?author=%s"
    _const_feed_favorites_ = "http://gdata.youtube.com/feeds/users/%s/favorites"

    #Config args
    max = 0
    #filter type {0 = mostviewed, 1 = toprated, 2 = user}
    filter_type = 0
    #filter user type {0 = upload, 1 = favorites}
    user_filter_type = 0
    username = ""
    

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.entries = None

    def initialize(self):
        return True

    def configure(self, window):
        tree = Utils.dataprovider_glade_get_widget (
                __file__,
                "config.glade",
                "YouTubeSourceConfigDialog") 

        dlg = tree.get_widget ("YouTubeSourceConfigDialog")
        mostviewedRb = tree.get_widget("mostviewed")
        topratedRb = tree.get_widget("toprated")
        byuserRb = tree.get_widget("byuser")
        user_frame = tree.get_widget("frame")
        uploadedbyRb = tree.get_widget("uploadedby")
        favoritesofRb = tree.get_widget("favoritesof")
        user = tree.get_widget("user")
        maxdownloads = tree.get_widget("maxdownloads")

        byuserRb.connect("toggled", self._filter_user_toggled_cb, user_frame)

        if self.filter_type == 0:
            mostviewedRb.set_active(True)
        elif self.filter_type == 1:
            topratedRb.set_active(True)
        else:
            byuserRb.set_active(True)
            user_frame.set_sensitive(True)
            if self.user_filter_type == 0:
                uploadedbyRb.set_active(True)
            else:
                favoritesofRb.set_active(True)
            user.set_text(self.username)

        logging.debug("Max")
        logging.debug(self.max)
        maxdownloads.set_value(self.max)

        response = Utils.run_dialog(dlg, window)
        if response == gtk.RESPONSE_OK:
            if mostviewedRb.get_active():
                self.filter_type = 0
            elif topratedRb.get_active():
                self.filter_type = 1
            else:
                self.filter_type = 2
                if uploadedbyRb.get_active():
                    self.user_filter_type = 0
                else:
                    self.user_filter_type = 1
                self.username = user.get_text()
            self.max = int(maxdownloads.get_value())
        
        dlg.destroy()

    def refresh(self):
        DataProvider.DataSource.refresh(self)

        self.entries = {}
        try:
            feedUrl = ""
            if self.filter_type == 0:
                feedUrl = self._const_feed_most_viewed_
            elif self.filter_type == 1:
                feedUrl = self._const_feed_top_rated_ 
            else:
                if self.user_filter_type == 0:
                    feedUrl = (self._const_feed_upload_by_ %  self.username)
                else:
                    feedUrl = (self._const_feed_favorites_ % self.username)

            if self.max > 0:
                feedUrl = ("%s&max-results=%d" % (feedUrl, self.max))

            logging.debug ("Retrieve URL: %s" % feedUrl)
            url_info = urllib2.urlopen(feedUrl)
            if (url_info):
                doc = ElementTree.parse(url_info).getroot()
                for entry in doc.findall("{http://www.w3.org/2005/Atom}entry"):
                    for c in entry.getchildren():
                        if (c.tag == "{http://www.w3.org/2005/Atom}title"):
                            title = c.text
                        if (c.tag =="{http://search.yahoo.com/mrss/}group"):
                            for cc in c.getchildren():
                                if (cc.tag == "{http://search.yahoo.com/mrss/}player"):
                                    url = cc.get("url")

                    self.entries[title] = url
        except:
            logging.debug("Error getting/parsing feed \n%s" % traceback.format_exc())
            raise Exceptions.RefreshError

    def get_all(self):
        return self.entries.keys()
            
    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        
        url = self.entries[LUID]
        logging.debug("Title: '%s', Url: '%s'"%(LUID, url))
        video_url = self._extract_video_url (url)
        logging.debug ("URL: %s" % video_url)

        f = File.File (URI=video_url)
        f.set_open_URI (video_url)
        f.set_UID(LUID)
        f.force_new_filename (LUID + ".flv")

        return f

    def finish(self):
        DataProvider.DataSource.finish(self)
        self.files = None

    def get_configuration(self):
        return {
            "filter_type" : self.filter_type,
            "user_filter_type" : self.user_filter_type,
            "username" : self.username,
            "max" : self.max
        }
            

    def get_UID(self):
        return Utils.get_user_string()

    #ui callbacks
    def _filter_user_toggled_cb (self, toggle, frame):
        frame.set_sensitive(toggle.get_active())

    # Generic extract step
    def _extract_video_url (self, url):
        regexp = re.compile(r'[,{]t:\'([^\']*)\'')

        try:
            doc = urllib2.urlopen(url)
            data = doc.read()

            #extract video name
            match = regexp.search(data)
            if match is None:
                return None
            video_name = match.group(1)

            #extract video id
            url_splited = url.split ("watch?v=")
            video_id = url_splited[1]     

            url = "http://www.youtube.com/get_video?video_id=%s&t=%s" % (video_id, video_name)
            return url
    
        except:
            log("Error getting/parsing feed \n%s" % traceback.format_exc())
            return None

