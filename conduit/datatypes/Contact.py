import conduit
from conduit import log,logd,logw
from conduit.datatypes import DataType

import vobject

class Contact(DataType.DataType):
    """
    Very basic contact representation
    """
    def __init__(self, URI, **kwargs):
        DataType.DataType.__init__(self, "contact")
        self.vCard = vobject.vCard()

        self.set_open_URI(URI)

    def set_from_vcard_string(self, string):
        self.vCard = vobject.readOne(string)

    def get_vcard_string(self, version=2.1):
        return self.vCard.serialize()

    def compare(self, B):
        return conduit.datatypes.COMPARISON_UNKNOWN

    def __getstate__(self):
        """
        Store the object state in a dict for pickling
        """
        data = {}
        data['vcard'] = self.get_vcard_string()
        data['mtime'] = self.get_mtime()
        data['uid'] = self.get_UID()
        data['open_uri'] = self.get_open_URI()
        return data

    def __setstate__(self, data):
        """
        Set object state from dict (after unpickling)
        """
        self.set_from_vcard_string(data['vcard'])
        self.set_mtime(data['mtime'])
        self.set_UID(data['uid'])
        self.set_open_URI(data['open_uri'])

    def __str__(self):
        return self.get_vcard_string()

