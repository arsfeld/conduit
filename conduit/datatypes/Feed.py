import conduit
from conduit.datatypes import DataType

class Feed(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self,"feed")

        #Pretty much took these from the opml file
        self.title = ""
        self.description = ""
        self.htmlUrl = ""
        self.xmlUrl = ""        
        self.lastAccessed = ""
