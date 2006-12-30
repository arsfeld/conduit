import conduit
import conduit.evolution
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
        print conduit.evolution.search_sync("John", 10)
