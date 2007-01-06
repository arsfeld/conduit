import conduit
import conduit.Utils as Utils

import conduit.datatypes.Contact as Contact

MODULES = {
	"ContactConverter" : { "type": "converter" }
}

class ContactConverter:
    def __init__(self):
        self.conversions =  {    
                            "contact,file"    : self.to_file,
                            "contact,text"    : self.to_text,
                            "file,contact"    : self.file_to_contact,
                            }
                            
    def to_file(self, contact):
        #FIXME: Save contact as a VCard
        return Utils.new_tempfile(str(contact))

    def to_text(self, contact):
        return str(contact)

    def file_to_contact(self, f):
        c = Contact.Contact()
        c.readVCard(f.get_contents_as_text())
        return c

