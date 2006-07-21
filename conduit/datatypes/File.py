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
