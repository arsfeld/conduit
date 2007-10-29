import conduit
import conduit.Utils as Utils
import conduit.datatypes.File as File
import conduit.datatypes.Photo as Photo

MODULES = {
        "PixbufPhotoConverter" :  { "type": "converter" }
}

class PixbufPhotoConverter:
    def __init__(self):
        self.conversions =  {
                            "file/photo,file/photo"     :   self.transcode,    
                            "file,file/photo"           :   self.file_to_photo
                            }
        self._image_types = None
                            
    def _get_pixbuf_capabilities(self):
        """
        Returns a dict mapping image mimetypes to extensions to 
        be used when converting image formats
        """
        if self._image_types == None:
            import gtk.gdk
            types = {}
            for f in gtk.gdk.pixbuf_get_formats():
                for t in f["mime_types"]:
                    if f["is_writable"] == True:
                        types[t] = f["extensions"][0]
                    else:
                        types[t] = None
            self._image_types = types
        return self._image_types

    def transcode(self, photo, **kwargs):
        conduit.log("Transcode Photo: %s" % kwargs)
        formats = kwargs.get("formats","").split(',')
        newSize = kwargs.get("size","")

        #check if the photo is in the allowed format
        if photo.get_mimetype() not in formats:
            #convert photo to default format
            mimeType = kwargs.get("default-format","image/jpeg")
            #now look up the appropriate conversion
            try:
                newFormat = self._get_pixbuf_capabilities()["mimeType"]
            except KeyError:
                newFormat = "jpeg"
        else:
            newFormat = None

        photo.convert(format=newFormat, size=newSize)
        return photo

    def file_to_photo(self, f, **kwargs):
        t = f.get_mimetype()
        if t in self._get_pixbuf_capabilities().keys():
            return self.transcode(
                            Photo.Photo(URI=f._get_text_uri()),
                            **kwargs
                            )
        else:
            return None
            
