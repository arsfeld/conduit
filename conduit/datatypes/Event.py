import vobject 
import re
import conduit.datatypes.DataType as DataType

class Event(DataType.DataType):
    """
    Very basic calendar event representation
    """
    _name_ = "event"
    def __init__(self, **kwargs):
        DataType.DataType.__init__(self)
        self.iCal = vobject.iCalendar()

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
        ical_string = self.get_ical_string()
        p = re.compile('CREATED:.*\n')
        ical_string = p.sub( '', ical_string )
        p = re.compile('LAST-MODIFIED:.*\n')
        ical_string = p.sub( '', ical_string )
        p = re.compile('UID:.*\n')
        ical_string = p.sub( '', ical_string )
        return str(hash(ical_string))
