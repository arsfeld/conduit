import conduit
from conduit.datatypes import DataType

class Text(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self,"text")

        self.raw = ""
        self.decodedText = ""
        self.modified = None
        self.title = ""
    
    def decode(text, dateRegex, titleRegex):
        self.decodedText = "Decoded"
