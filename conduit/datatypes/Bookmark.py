# (c) Copyright Andrew Stormont <andyjstormont@googlemail.com> 2008.

import logging
log = logging.getLogger("datatypes.Bookmark")

import conduit
from conduit.datatypes import DataType

class Bookmark(DataType.DataType):
    """
    Represents a Bookmark with a title and uri
    """
    _name_ = "Bookmark"
    def __init__(self, title, uri, **kwargs):
        DataType.DataType.__init__(self)
        self.title = title
        self.uri = uri

    def get_title(self):
        return self.title

    def get_uri(self):
        return self.uri
        
    def get_hash(self):
        return str(hash( (self.get_title(), self.get_uri()) ))

    def get_bookmark_string(self):
        return self.__str__()

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data["title"] = self.get_title()
        data["uri"] = self.get_uri()
        return data

    def __setstate__(self, data):
        self.title = data["title"]
        self.uri = data["uri"]
        DataType.DataType.__setstate__(self, data)

    def __str__(self):
        return "%s:%s" % (self.get_title(), self.get_uri() )

