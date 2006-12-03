import sys, os
import logging
import conduit
from conduit.datatypes import DataType

try:
    import vobject
except ImportError:
    logging.warn("Note: Using built in vobject")
    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"vobject-0.4.4"))
    import vobject

class Contact(DataType.DataType):
    """
    Very basic contact representation
    """
    def __init__(self, friendlyName="", name=""):
        DataType.DataType.__init__(self, "contact")
        
        self.vCard = vobject.vCard()

        self.vCard.add('fn')
        self.vCard.fn.value = friendlyName

        self.vCard.add('n')
        self.vCard.n.value = vobject.vcard.Name( family='Harris', given='Jeffrey' )

    def readVCard(self, string):
        self.vCard = vobject.readOne(string)

    def compare(self, A, B):
        return conduit.datatypes.UNKNOWN

    def __str__(self):
        return self.vCard.serialize()

