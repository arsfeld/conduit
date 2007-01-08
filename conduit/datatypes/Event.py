import sys, os
import logging
import conduit
from conduit.datatypes import DataType

import vobject

class Event(DataType.DataType):
    """
    Very basic calendar event representation
    """
    def __init__(self, friendlyName="", name=""):
        DataType.DataType.__init__(self, "event")
        self.iCal = vobject.iCalendar()

    def read_string(self, string):
        self.iCal = vobject.readOne(string)

    def to_string(self):
        return self.iCal.serialize()

    def compare(self, A, B):
        return conduit.datatypes.UNKNOWN


