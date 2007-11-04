import conduit

import conduit.datatypes.File as File
import conduit.Utils as Utils

PRESET_ENCODINGS = {
    "jpeg":{'formats':'image/jpeg','default-format':'image/jpeg'},
    "png":{'formats':'image/png','default-format':'image/png'}
    }

class Photo(File.File):
    """
    A Small wrapper around a Pixbuf
    """

    _name_ = "file/photo"

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)
        self.pb = None

    def get_pixbuf(self):
        """
        Defer actually getting the pixbuf till as
        late as possible, as it is really only needed for
        conversion
        """
        import gtk.gdk
        if self.pb == None:
            self.pb = gtk.gdk.pixbuf_new_from_file(self.get_local_uri())
        return self.pb

    def get_size(self):
        """
        Returns the pb size, width, height
        """
        self.get_pixbuf()
        return self.pb.get_width(),self.pb.get_height()        


