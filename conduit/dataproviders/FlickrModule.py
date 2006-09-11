"""
Flickr Uploader.

Code Borrowed from postr, ross burtoni
"""
import os, sys
import gtk

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions

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
		"category": DataProvider.CATEGORY_WEB,
		"in_type": "taggedfile",
		"out_type": "taggedfile"
	},
	"TaggedFileConverter" : {
		"name": "Tagged File Converter",
		"description": "",
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": "",
	}           
}

class FlickrSink(DataProvider.DataSink):
    API_KEY="65552e8722b21d299388120c9fa33580"
    SHARED_SECRET="03182987bf7fc4d1"
    ALLOWED_MIMETYPES = ["image/jpeg", "image/png"]
    
    def __init__(self):
        DataProvider.DataSink.__init__(self, "Flickr Sink", "Your Photos")
        self.icon_name = "image-x-generic"
        
        self.fapi = None
        self.token = None
        self.tagWith = "Conduit"
        self.showPublic = True
        self.showFriends = True
        self.showFamily = True
        
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

        mimeType = photo.get_mimetype()
        if mimeType not in FlickrSink.ALLOWED_MIMETYPES:
            raise Exceptions.SyncronizeError("Flickr does not allow uploading %s Files" % mimeType)
        
            
        logging.debug("Photo URI = %s, Mimetype = %s" % (photoURI, mimeType))
        ret = self.fapi.upload( api_key=FlickrSink.API_KEY, 
                                auth_token=self.token,
                                filename=photoURI,
                                )
        if self.fapi.getRspErrorCode(ret) != 0:
            raise Exceptions.SyncronizeError("Flickr Upload Error: %s" % fapi.getPrintableError(ret))

    def configure(self, window):
        """
        Configures the GmailSource for which emails it should return
        
        All the inner function foo is because the allEmail
        option is mutually exclusive with all the others (which may be
        mixed according to the users preferences
        """
        tree = gtk.glade.XML(conduit.GLADE_FILE, "FlickrSinkConfigDialog")
        
        #get a whole bunch of widgets
        attachTagCb = tree.get_widget("attach_tag_check")
        tagEntry = tree.get_widget("tag_entry")
        publicCb = tree.get_widget("public_check")
        friendsCb = tree.get_widget("friends_check")
        familyCb = tree.get_widget("family_check")
        
        #preload the widgets
        attachTagCb.set_active(len(self.tagWith) > 0)
        tagEntry.set_text(self.tagWith)
        publicCb.set_active(self.showPublic)
        friendsCb.set_active(self.showFriends)
        familyCb.set_active(self.showFamily)
        
        
        dlg = tree.get_widget("FlickrSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            if attachTagCb.get_active():
                self.tagWith = tagEntry.get_text()
            self.showPublic = publicCb.get_active()
            self.showFamily = familyCb.get_active()
            self.showFriends = friendsCb.get_active()                        
        dlg.destroy()    
        
    def get_configuration(self):
        return {
            "tagWith" : self.tagWith,
            "showPublic" : self.showPublic,
            "showFriends" : self.showFriends,
            "showFamily" : self.showFamily
            }
            
class TaggedFileConverter:
    def __init__(self):
        self.conversions =  {    
                            "taggedfile,file" : self.taggedfile_to_file,
                            }            
    def taggedfile_to_file(self, thefile):
        #taggedfile is parent class of file so no conversion neccessary
        return thefile
