import gtk.gdk
import conduit

from conduit.datatypes import File

class Photo(File.File):
    """
    A Small wrapper around a Pixbuf
    """

    _name_ = "file/photo"

    def __init__(self, URI, pb=None):
        File.File.__init__(self, URI=URI)
        self.pb = pb

    def get_pixbuf(self):
        """
        Defer actually getting the pixbuf till as
        late as possible, as it is really only needed for
        conversion
        """
        if self.pb == None:
            self.pb = gtk.gdk.pixbuf_new_from_file(self.get_local_filename())
        return self.pb

    def get_size(self):
        """
        Returns the pb size, width, height
        """
        self.get_pixbuf()
        return self.pb.get_width(),self.pb.get_height()


        
