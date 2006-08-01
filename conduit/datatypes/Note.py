import conduit
from conduit.datatypes import DataType

class Note(DataType.DataType):
    def __init__(self, title="", modified=None, contents=""):
        DataType.DataType.__init__(self,"note")

        self.title = title
        self.modified = modified
        self.contents = contents
        self.createdUsing = ""
        
    def __str__(self):
        return ("Title: %s\n%s\n(Modified: %s)" % (self.title, self.contents, self.modified))
        

