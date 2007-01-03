import conduit
import conduit.Utils as Utils

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
        return Utils.new_tempfile(str(contact))

    def to_text(self, contact):
        return str(contact)

