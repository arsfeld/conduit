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
                self.pb = self.pb.scale_simple(int(width),int(height),gtk.gdk.INTERP_HYPER)
            except Exception, err:
                print "BUGGER", size, err
        
        #save to new format if necessary
        if format != None:
            print "Save %s.%s" % (tmpfilename,format)
            self.pb.save("%s.%s" % (tmpfilename,format), format)
        
        
