import gtk.gdk
import conduit

import conduit.Utils as Utils
import conduit.datatypes.File as File
import conduit.datatypes.Photo as Photo
import conduit.datatypes.Music as Music

MODULES = {
        "PixbufPhotoConverter" :  { "type": "converter" }
}

def get_pixbuf_capabilities():
    """
    Returns a dict mapping image mimetypes to extensions to 
    be used when converting image formats
    """
    types = {}
    for f in gtk.gdk.pixbuf_get_formats():
        for t in f["mime_types"]:
            if f["is_writable"] == True:
                types[t] = f["extensions"][0]
            else:
                types[t] = None
    return types

class PixbufPhotoConverter:

    IMAGE_TYPES = get_pixbuf_capabilities()

    def __init__(self):
        self.conversions =  {
                            "file/photo,file/photo"     :   self.transcode,    
                            "file,file/photo"           :   self.file_to_photo
                            }
                            
    def transcode(self, photo, **kwargs):
        conduit.log("Transcode Photo: %s" % kwargs)
        formats = kwargs.get("formats","").split(',')
        newSize = kwargs.get("size",None)

        #check if the photo is in the allowed format
        if photo.get_mimetype() not in formats:
            #convert photo to default format
            mimeType = kwargs.get("default-format","image/jpeg")
            #now look up the appropriate conversion
            try:
                newFormat = PixbufPhotoConverter.IMAGE_TYPES["mimeType"]
            except KeyError:
                newFormat = "jpeg"
        else:
            newFormat = None

        photo.convert(format=newFormat, size=newSize)
        return photo

    def file_to_photo(self, f, **kwargs):
        t = f.get_mimetype()
        if t in PixbufPhotoConverter.IMAGE_TYPES.keys():
            return self.transcode(
                            Photo.Photo(URI=f._get_text_uri()),
                            **kwargs
                            )
        else:
            print "NONE"
            return None
            
