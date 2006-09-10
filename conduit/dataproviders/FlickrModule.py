"""
Flickr Uploader.

Code Borrowed from postr, ross burtoni
"""
import logging
import conduit
import conduit.DataProvider as DataProvider

import os, sys

try:
    from flickrapi import FlickrAPI
except ImportError:
    logging.warn("Note: Using built in flickrapi")
    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"FlickrAPI-8"))
    from flickrapi import FlickrAPI

#try:
#    import EXIF
#except ImportError:
#    logging.warn("Note: Using built in EXIF")
#    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"EXIF-15-FEB-04"))
#    import EXIF


MODULES = {
	"FlickrSink" : {
		"name": "Flickr Sink",
		"description": "Your Photos",
		"type": "sink",
		"category": "Test",
		"in_type": "file",
		"out_type": "file"
	}
}

class FlickrSink(DataProvider.DataSink):
    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"
    
    def __init__(self):
        DataProvider.DataSink.__init__(self, "Flickr Sink", "Your Photos")
        self.icon_name = "image-x-generic"
        
        self.fapi = None
        self.token = None
        
    def refresh(self):
        self.fapi = FlickrAPI(FlickrSink.API_KEY, FlickrSink.SHARED_SECRET)
        self.token = self.fapi.getToken(browser="gnome-www-browser", perms="write")
        
    def put(self, photo, photoOnTop=None):
        """
        Accepts a vfs file. Must be made local
        """
        #Gets the local URI (/foo/bar). If this is a remote file then
        #it is first transferred to the local filesystem
        photoURI = photo.get_local_filename()
        #FIXME: Only allow jpegs
        #mimeType = photo.get_mimetype()
            
        logging.debug("Photo URI = %s" % photoURI)
        ret = self.fapi.upload( api_key=FlickrSink.API_KEY, 
                                auth_token=self.token,
                                filename=photoURI,
                                )
        if self.fapi.getRspErrorCode(ret) != 0:
                logging.error("Flickr Upload Error: %s" % fapi.getPrintableError(ret))
