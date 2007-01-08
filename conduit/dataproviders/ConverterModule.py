import logging
import conduit
import conduit.Utils as Utils
import conduit.datatypes.Contact as Contact

MODULES = {
	"TextConverter" :       { "type": "converter" },
	"ContactConverter" :    { "type": "converter" },
	"TaggedFileConverter" : { "type": "converter" }
}

class TextConverter:
    def __init__(self):
        self.conversions =  {    
                            "email,text"    : self.to_text,
                            "note,text"     : self.to_text
                            }
                            
                            
    def to_text(self, measure):
        """
        Cheat and hope that modules define __str__()
        """
        if hasattr(measure, "__str__"):
            return str(measure)
        logging.warn("%s does not define __str__()" % measure)
        return ""

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

class TaggedFileConverter:
    def __init__(self):
        self.conversions =  {    
                            "taggedfile,file" : self.taggedfile_to_file,
                            "file,taggedfile" : self.file_to_taggedfile
                            }            
    def taggedfile_to_file(self, thefile):
        #taggedfile is parent class of file so no conversion neccessary
        return thefile

    def file_to_taggedfile(self, thefile):
        #FIXME: Save URI and kwargs and then chain this on to the new type
        #This means all datatypes must have the same prototype
        #DataType(uri, **kwargs)
        return thefile

