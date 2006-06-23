from gettext import gettext as _

import DataType

MODULES = {
	"FileDataType" : {
		"name": _("File Data Type"),
		"description": _("Represents a Data Type"),
		"type": "datatype"
	}
}

#TODO: Inherit from Source
class FileDataType(DataType.DataType):
	def __init__(self):
		DataType.DataType.__init__(self, _("File Data Type"), _("Represents a Data Type"))
		

