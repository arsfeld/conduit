import conduit

import conduit.datatypes.File as File
import conduit.Utils as Utils

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
        
    def __getstate__(self):
        return File.File.__getstate__(self)

    def __setstate__(self, data):
        self.pb = None
        File.File.__setstate__(self, data)


