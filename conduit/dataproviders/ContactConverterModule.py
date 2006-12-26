from gettext import gettext as _
import logging
import conduit
import conduit.datatypes.File as File

MODULES = {
	"ContactConverter" : { "type": "converter" }
}

class ContactConverter:
    def __init__(self):
        self.conversions =  {    
                            "contact,file"    : self.to_file,
                            "contact,text"    : self.to_text
                            }
                            
    def to_file(self, contact):
        #FIXME: Save contact as a VCard
        return File.new_from_tempfile(str(contact))

    def to_text(self, contact):
        return str(contact)

