import gtk
from gettext import gettext as _

import logging
import conduit
import DataProvider
import DataType

import xmlrpclib

MODULES = {
	"MoinMoinDataSource" : {
		"name": _("Wiki Source"),
		"description": _("Moinmoin Wiki Source"),
		"type": "source",
		"category": "Local",
		"in_type": "wikipage",
		"out_type": "wikipage"
	},
	"WikiPageDataType" : {
		"name": _("Wiki Page Data Type"),
		"description": _("Represents a Moinmoin wiki page"),
		"type": "datatype",
		"category": "",
		"in_type": "wikipage",
		"out_type": "wikipage"		
	}
}

class MoinMoinDataSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("Wiki Source"), _("Moinmoin Wiki Source"))
        self.icon_name = "gtk-file"
        
        #class specific
        self.srcwiki = None
        self.pages = []
        
    def configure(self, window):
        def set_pages(param):
            self.pages = param.split(',')
            logging.debug("Configured pages = %s" % self.pages)            
        
        #Define the items in the configure dialogue
        items = [
                    {
                    "Name" : "Page Names to Synchronize:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_pages
                    }                    
                ]
        #We just use a simple configuration dialog
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        #This call blocks
        dialog.run()
        
    def initialize(self):
        if self.srcwiki is None:
            self.srcwiki = xmlrpclib.ServerProxy("http://live.gnome.org/?action=xmlrpc2")
        self.set_status(DataProvider.STATUS_DONE_INIT_OK)
            
    def finalize(self):
            self.srcwiki = None
            
    def get(self):
        #for p in pages:
        #    pageinfo = srcwiki.getPageInfo(p)
        #    pagedata = srcwiki.getPage(p)
        #    print "Page Info: name=%s, modified=%s, author=%s, version=%s" % (
        #                                        pageinfo["name"], 
        #                                        pageinfo["lastModified"], 
        #                                        pageinfo["author"], pageinfo["version"]
        #                                        )            
        pass
		
class WikiPageDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, _("Wiki Page Data Type"), _("Represents a Moinmoin wiki page"))
        self.conversions =  {    
                            "text,wikipage" : self.text_to_wikipage,
                            "wikipage,text"   : self.wikipage_to_text
                            }
                            
        #Instance variables
        self.pageData = ""
        self.pageName = "" 
        self.pageModified = ""
        
    def text_to_wikipage(self, measure):
        return "text->wikipage = ", str(measure)

    def wikipage_to_text(self, measure):
        return "wikipage->text = ", str(measure)
