import logging
import conduit
from conduit.datatypes import DataType

class Contact(DataType.DataType):
    """
    Very basic contact representation
    """
    def __init__(self, formattedName="", email=""):
        DataType.DataType.__init__(self, "contact")

        self.formattedName = formattedName
        self.email = email
        self.name = ""
        self.birthday = ""

    def compare(self, A, B):
        return conduit.datatypes.UNKNOWN

    def __str__(self):
        return ("formatedName: %s\nEmail: %s\n" % (self.formattedName,self.email))

