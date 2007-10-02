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
            self.pb = gtk.gdk.pixbuf_new_from_file(self.get_local_uri())
        return self.pb

    def get_size(self):
        """
        Returns the pb size, width, height
        """
        self.get_pixbuf()
        return self.pb.get_width(),self.pb.get_height()
        
    def _get_proportional_resize(self, newWidth, newHeight):
        w,h = self.get_size()
        # resize to fit in frame
        if h < w:
            width = newWidth
            height = float(newWidth) / w * h
        else:
            height = newHeight
            width = float(newHeight) / h * w

        return int(width), int(height)

    def convert(self, format, size):
        """
        Basically we defer the conversion until as late as possible, or 
        not at all.
        """
        if format == None and size == None:
            return

        #copy the folder to the temp dir
        tmpfilename = self._to_tempfile()
        self.pb = gtk.gdk.pixbuf_new_from_file(tmpfilename)
        
        #resize if necessary
        if size != None:
            try:
                width,height = size.split('x')
                width,height = self._get_proportional_resize(int(width), int(height))
                print "SCALING TO %sx%s" % (width,height)
                self.pb = self.pb.scale_simple(width,height,gtk.gdk.INTERP_HYPER)
                self.pb.save(tmpfilename , "jpeg")
            except Exception, err:
                print "BUGGER", size, err
        
        #save to new format if necessary
        if format != None:
            print "Save %s.%s" % (tmpfilename,format)
            self.pb.save(tmpfilename, format)
        
        
