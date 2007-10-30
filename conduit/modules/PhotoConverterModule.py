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
        
    def _convert(self, pb, out_file, format, width, height):
        """
        Basically we defer the conversion until as late as possible, or 
        not at all.
        """
        import gtk.gdk
        #resize if necessary
        if width != None and height != None:
            try:
                print "SCALING TO %sx%s" % (width,height)
                pb = pb.scale_simple(width,height,gtk.gdk.INTERP_HYPER)
                #make sure we save the resized image
                if format == None: 
                    format = "jpeg"
            except Exception, err:
                print "BUGGER", size, err
        
        #save to new format if necessary
        if format != None:
            print "Save %s.%s" % (out_file,format)
            pb.save(out_file, format)

    def transcode(self, photo, **kwargs):
        conduit.log("Transcode Photo: %s" % kwargs)
        formats = kwargs.get("formats","").split(',')
        newSize = kwargs.get("size",None)
        
        #anything to do?
        if len(formats) == 0 and newSize == None:
            return photo

        #check if the photo is in the allowed format
        if photo.get_mimetype() not in formats:
            #convert photo to default format
            mimeType = kwargs.get("default-format","image/jpeg")
            try:
                newFormat = self._get_pixbuf_capabilities()[mimeType]
            except KeyError:
                newFormat = "jpeg"
        else:
            newFormat = None
            
        #resize if necessary
        if newSize != None:
            w,h = photo.get_size()
            width,height = Utils.get_proportional_resize(
                                desiredW=int(newSize.split('x')[0]),
                                desiredH=int(newSize.split('x')[1]),
                                currentW=int(w),
                                currentH=int(h)
                                )
        else:
            width = None
            height = None

        input_pb = photo.get_pixbuf()
        output_file = photo.to_tempfile()
        self._convert(
                input_pb,
                output_file,
                newFormat,
                width,
                height
                )
                
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
            
