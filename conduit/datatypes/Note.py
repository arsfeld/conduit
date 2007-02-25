import conduit
from conduit import log,logd,logw
from conduit.datatypes import DataType

class Note(DataType.DataType):
    """
    Represents a Note
    """
    def __init__(self, URI, **kwargs):
        """
        Note constructor.

        kwargs understands a number of different keys:
          - title: The title of the note
          - contents: The raw note contents
          - modified: Unix timestamp modified time
        """
        DataType.DataType.__init__(self,"note")

        self.title = kwargs.get("title", "")
        self.contents = kwargs.get("contents","")
        self.modified = kwargs.get("modified", None)

        self.set_open_URI(URI)
        self.set_mtime(self.modified)

    def set_from_note_string(self, string):
        raise NotImplementedError

    def get_note_string(self):
        return ("Title: %s\n%s\n(Modified: %s)" % (self.title, self.contents, self.modified))
        
    def __str__(self):
        return self.title
        


