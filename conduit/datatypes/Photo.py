import conduit

import conduit.datatypes.File as File
import conduit.utils as Utils
import logging
log = logging.getLogger("datatypes.Photo")

PRESET_ENCODINGS = {
    "jpeg":{'formats':'image/jpeg','default-format':'image/jpeg'},
    "png":{'formats':'image/png','default-format':'image/png'}
    }
    
def mimetype_is_photo(mimetype):
    """
    @returns: True if the given mimetype string represents an image file
    """
    if mimetype.startswith("image/"):
        return True
    else:
        return False

class Photo(File.File):
    """
    A Small wrapper around a Pixbuf
    """

    _name_ = "file/photo"

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)
        self.pb = None
        self._caption = None

    def compare(self, B, sizeOnly=False):
        if sizeOnly:
            return File.File.compare(self, B, True)

        meTime = self.get_mtime()
        bTime = B.get_mtime()
        log.debug("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (self.URI, meTime, B.URI, bTime))
        if meTime and bTime and (meTime != bTime):
            if meTime > bTime:    #Am I newer than B
                return conduit.datatypes.COMPARISON_NEWER        
            else:
                return conduit.datatypes.COMPARISON_OLDER

        meHash = self.get_hash()
        bHash = B.get_hash()
        log.debug("Comparing %s (HASH: %s) with %s (HASH: %s)" % (self.URI, meHash, B.URI, bHash))
        if (meHash == bHash):
            return conduit.datatypes.COMPARISON_EQUAL
        else:
            return conduit.datatypes.COMPARISON_UNKNOWN

    def get_photo_pixbuf(self):
        """
        Defer actually getting the pixbuf till as
        late as possible, as it is really only needed for
        conversion
        """
        import gtk.gdk
        if self.pb == None:
            self.pb = gtk.gdk.pixbuf_new_from_file(self.get_local_uri())
        return self.pb

    def get_photo_size(self):
        """
        Returns the pb size, width, height
        """
        self.get_photo_pixbuf()
        return self.pb.get_width(),self.pb.get_height()

    def get_caption(self):
        """
        @returns: the photo's caption
        """
        return self._caption

    def set_caption(self, caption):
        self._caption = caption

    def get_hash(self):
        # Combine the file hash with other photo metadata.
        file_hash = File.File.get_hash(self)       
        hash_data = "%s%s%s" % (file_hash, self.get_photo_size(),
                self.get_caption())
        return str(hash(hash_data))
        
    def __getstate__(self):
        data = File.File.__getstate__(self)
        data["caption"] = self._caption
        return data

    def __setstate__(self, data):
        self.pb = None
        self._caption = data["caption"]
        File.File.__setstate__(self, data)


