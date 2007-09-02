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
import conduit.DataProvider as DataProvider
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

class YouTubeEntry:
    Title = ""
    Url = ""
    def __init__ (self, title, url):
        self.Title = title
        self.Url = url


class YouTubeSource(DataProvider.DataSource):

    _name_ = _("YouTube")
    _description_ = _("Sync data from YouTube")
    _category_ = DataProvider.CATEGORY_MISC
    _module_type_ = "source"
    _in_type_ = ""
    _out_type_ = "file"
    _icon_ = "youtube"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        
        self.feedUrl = "http://gdata.youtube.com/feeds/standardfeeds/top_rated?time=today"
        #self.feedUrl = ""
        self.entries = None

    def initialize(self):
        return True

    def configure(self, window):
        return None

    def refresh(self):
        DataProvider.DataSource.refresh(self)

        self.entries = {}
        try:
            logging.debug("Open")
            url_info = urllib2.urlopen(self.feedUrl)
            if (url_info):
                logging.debug("Parse")
                doc = ElementTree.parse(url_info).getroot()
                for entry in doc.findall("{http://www.w3.org/2005/Atom}entry"):


                    for c in entry.getchildren():
                        if (c.tag == "{http://www.w3.org/2005/Atom}title"):
                            title = c.text
                        if (c.tag =="{http://search.yahoo.com/mrss/}group"):
                            logging.debug ("Has group")
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
        video_url = self.extract_video_url (url)
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
        return None

    def get_UID(self):
        return self.feedUrl

    # Generic extract step
    def extract_video_url (self, url):
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

