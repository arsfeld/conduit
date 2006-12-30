import conduit
import conduit.evolution as evo
import conduit.DataProvider as DataProvider

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
              
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #API USAGE EXAMPLE
        books = evo.list_addressbooks()
        print "AVAILABLE ADDRESSBOOKS: ",books
        book = evo.open_addressbook('default')
        print "AVAILABLE CONTACTS"
        for i in book.get_all_contacts():
            #PROPERTY ACCESS            
            print i.get_property("name-or-org")
            #PRINTS TO VCARD
            #print i.get_vcard_string()
