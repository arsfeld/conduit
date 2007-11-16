import vobject 

import conduit
from conduit.datatypes import DataType

class Event(DataType.DataType):
    """
    Very basic calendar event representation
    """

    _name_ = "event"

    def __init__(self, URI, **kwargs):
        DataType.DataType.__init__(self)
        self.iCal = vobject.iCalendar()

        self.set_open_URI(URI)

    def set_from_ical_string(self, string):
        self.iCal = vobject.readOne(string)

    def get_ical_string(self, version=1.0):
        return self.iCal.serialize()

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['ical'] = self.get_ical_string()
        return data

    def __setstate__(self, data):
        self.set_from_ical_string(data['ical'])
        DataType.DataType.__setstate__(self, data)
        
    def get_hash(self):
        return hash(self.iCal)
