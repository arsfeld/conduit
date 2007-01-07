import md5

import conduit
from conduit.datatypes import DataType

class Text(DataType.DataType):
    def __init__(self, uri, **kwargs):
        DataType.DataType.__init__(self,"text")
        self.text = ""
    
    def set_text(self, text):
        self.text = text

    def __str__(self):
        #only show first 20 characters
        if len(self.text) > 20:
            return self.text[0:19]
        else:
            return self.text

    def get_UID(self):
        return md5.new(self.text).hexdigest()
