from gettext import gettext as _

import DataType

MODULES = {
	"CalDataType" : {
		"name": _("Calendar Data Type"),
		"description": _("Represents an iCal"),
		"type": "datatype",
		"category": "",
		"in_type": "cal",
		"out_type": "cal",
	}
}

class CalDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, _("Calendar Data Type"), _("Represents an iCal"))
        self.conversions =  {    
                            "note" : self.note_to_cal
                            }
                            
        
    def note_to_cal(self, measure):
        return str(measure) + " was a note now is a cal"
