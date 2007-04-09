import evolution as evo

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider

import conduit.datatypes.Contact as Contact

MODULES = {
	"EvoContactSource" : { "type": "dataprovider" }	
}

class EvoContactSource(DataProvider.DataSource):

    _name_ = "Evolution Contacts"
    _description_ = "Sync your liferea RSS feeds"
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = ""

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.contacts = None
      
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.contacts = []

        #API USAGE EXAMPLE
        #books = evo.list_addressbooks()
        #print "AVAILABLE ADDRESSBOOKS: ",books
        
        book = evo.open_addressbook('default')
        for i in book.get_all_contacts():
            contact = Contact.Contact(None) #FIXME: Get the evolution URI
            contact.set_from_vcard_string(i.get_vcard_string())
            self.contacts.append(contact)

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return self.contacts[index]

    def finish(self):
        DataProvider.DataSource.finish(self)
        self.contacts = None

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return ""
