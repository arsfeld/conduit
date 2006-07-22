import conduit
from conduit.datatypes import DataType

class Note(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self,"note")

        self.title = ""
        self.modified = None
        self.contents = ""
        
    def __str__(self):
        return ("Title: %s\n%s\n(Modified: %s)" % (self.title, self.contents, self.modified))
        

