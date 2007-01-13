import conduit
from conduit.datatypes import DataType

class Note(DataType.DataType):
    def __init__(self, URI, **kwargs):
        DataType.DataType.__init__(self,"note")

        self.URI = URI
        self.title = kwargs.get("title", "")
        self.modified = kwargs.get("modified",None)
        self.contents = kwargs.get("contents","")
        
    def __str__(self):
        return ("Title: %s\n%s\n(Modified: %s)" % (self.title, self.contents, self.modified))
        

