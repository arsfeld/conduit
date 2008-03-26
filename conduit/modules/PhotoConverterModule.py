import logging
log = logging.getLogger("modules.PhotoConverter")

import conduit
import conduit.utils as Utils
import conduit.TypeConverter as TypeConverter
import conduit.datatypes.File as File
import conduit.datatypes.Photo as Photo

MODULES = {
        "PixbufPhotoConverter" :  { "type": "converter" }
}

NO_RESIZE = "None"

class PixbufPhotoConverter(TypeConverter.Converter):
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
        
    def _convert(self, photo, format, width, height, doResize, doReformat):
        """
        Basically we defer the conversion until as late as possible, or 
        not at all.
        """
        import gtk.gdk

        pb = photo.get_photo_pixbuf()
        out_file = photo.to_tempfile()

        if doResize:
            try:
                log.debug("Photo: Scaling to %sx%s" % (width,height))
                pb = pb.scale_simple(width,height,gtk.gdk.INTERP_HYPER)
            except Exception, err:
                log.debug("Photo: Error scaling photo\n%s" % err)
        
        #save to new format. gdk.Pixbuf needs the type argument
        if doResize or doReformat:
            log.debug("Photo: Saving photo:%s Format:%s" % (out_file,format))
            pb.save(out_file, format)
            #can safely rename the file here because its defintately a tempfile
            photo.force_new_file_extension(".%s" % format)

    def transcode(self, photo, **kwargs):
        log.info("Transcode Photo: %s" % kwargs)
        
        #default format is the current format, and default is no resize
        formats = kwargs.get("formats",photo.get_mimetype()).split(',')
        newSize = kwargs.get("size",NO_RESIZE)

        #resize if necessary
        if newSize != NO_RESIZE:
            w,h = photo.get_photo_size()
            width,height = Utils.get_proportional_resize(
                                desiredW=int(newSize.split('x')[0]),
                                desiredH=int(newSize.split('x')[1]),
                                currentW=int(w),
                                currentH=int(h)
                                )
            doResize = True
        else:
            width = None
            height = None
            doResize = False

        #check if the photo is in the allowed format, otherwise we must convert it
        mimeType = photo.get_mimetype()
        doReformat = False
        if mimeType not in formats:
            #convert photo to default format
            mimeType = kwargs.get("default-format","image/jpeg")
            doReformat = True

        #convert the mimetype to the image type for gdk pixbuf save method
        format = self._get_pixbuf_capabilities()[mimeType]
            
        self._convert(
                photo,
                format,
                width,
                height,
                doResize,
                doReformat
                )
                
        return photo

    def file_to_photo(self, f, **kwargs):
        t = f.get_mimetype()
        if t in self._get_pixbuf_capabilities().keys():
            p = Photo.Photo(
                        URI=f._get_text_uri()
                        )
            p.set_from_instance(f)
            return self.transcode(p,**kwargs)
        else:
            return None
            
