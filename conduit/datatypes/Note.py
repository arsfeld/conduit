import logging
log = logging.getLogger("datatypes.Note")

import conduit
from conduit.datatypes import DataType

class Note(DataType.DataType):
    """
    Represents a Note with a title and content
    """
    _name_ = "note"
    def __init__(self, title, contents, **kwargs):
        DataType.DataType.__init__(self)
        self.title = title
        self.contents = contents

    def get_title(self):
        return self.title

    def get_contents(self):
        return self.contents
        
    def get_hash(self):
        return str(hash( (self.get_title(), self.get_contents()) ))

    def get_note_string(self):
        return self.__str__()

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data["title"] = self.get_title()
        data["contents"] = self.get_contents()
        return data

    def __setstate__(self, data):
        self.title = data["title"]
        self.contents = data["contents"]
        DataType.DataType.__setstate__(self, data)
        
    def __str__(self):
        return ("Title: %s\n%s\n(Modified: %s)" % (self.get_title(), self.get_contents(), self.get_mtime()))

