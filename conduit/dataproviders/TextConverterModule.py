from gettext import gettext as _
import logging
import conduit

MODULES = {
	"TextConverter" : {
		"name": _("Bla"),
		"description": _("Bla"),
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": "",
	}
}

class TextConverter:
    def __init__(self):
        self.conversions =  {    
                            "email,text" : self.to_text
                            }
                            
                            
    def to_text(self, measure):
        """
        Cheat and hope that modules define __str__()
        """
        if hasattr(measure, "__str__"):
            return str(measure)
