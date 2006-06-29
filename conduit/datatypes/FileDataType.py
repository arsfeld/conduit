from gettext import gettext as _

import DataType

MODULES = {
	"FileDataType" : {
		"name": _("File Data Type"),
		"description": _("Represents a file on disk"),
		"type": "datatype",
		"category": "",
		"in_type": "file",
		"out_type": "file"		
	}
}

class FileDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, _("File Data Type"), _("Represents a file on disk"))
        self.conversions =  {    
                            "email" : self.email_to_file,
                            "cal"   : self.cal_to_file
                            }
                            
        
    def email_to_file(self, measure):
        return str(measure) + " was a email now is a file"

    def cal_to_file(self, measure):
        return str(measure) + " was a cal now is a file"
