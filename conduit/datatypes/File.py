import gnomevfs
import conduit
from conduit.datatypes import DataType

class File(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self,"file")

        self.uri = None                    
        self.vfsHandle = None
        
    def load_from_uri(self, uri):
        self.uri = uri
        self.vfsFile = gnomevfs.Handle(self.uri)
        
    def get_mimetype(self):
        info = gnomevfs.get_mime_type(self.uri)
        return info
        
    def get_filename(self):
        """
        Returns the filename of the file
        """
        return "Filename of vfsfile"
        
    def get_contents_as_text(self):
        return "Contents of File as text"
        
    def create_local_tempfile(self):
        """
        Creates a local temporary file copy of the vfs file. This is useful
        for non gnomevfs enabled libs

        @returns: local absolute path the the newly created temp file or
        None on error
        @rtype: C{string}
        """
        return "/home/john/Desktop/tempfile.txt"

        
