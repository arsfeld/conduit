import gtk.gdk
import conduit

import conduit.Utils as Utils
import conduit.datatypes.File as File
import conduit.datatypes.Music as Music

MODULES = {
        "PixbufPhotoConverter" :  { "type": "converter" }
}

class PixbufPhotoConverter:

    IMAGE_MIME_TYPES, WRITABLE_FORMATS = Utils.get_pixbuf_capabilities()

    def __init__(self):
        self.conversions =  {
                            "file/photo,file/photo"     :   self.transcode,    
                            "file,file/photo"           :   self.file_to_photo
                            }
                            
    def transcode(self, photo, **kwargs):
        conduit.log("Transcode Photo")
        size = kwargs.get("size",None)
        format = kwargs.get("format",None)
        quality = kwargs.get("quality",None)
        return photo

    def file_to_photo(self, f, **kwargs):
        t = f.get_mime_type()
        if t in PixbufPhotoConverter.IMAGE_MIME_TYPES:
            return self.transcode(
                            Photo.Photo(URI=f._get_text_uri(),
                            **kwargs
                            )
        else:
            return None
