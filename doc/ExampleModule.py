import gtk
from gettext import gettext as _

import logging
import conduit
import DataProvider
from conduit.datatypes import DataType
import conduit.Exceptions as Exceptions

import xmlrpclib

MODULES = {
	"MoinMoinDataSource" : {
		"name": _("GNOME Wiki Source"),
		"description": _("Get Pages from the GNOME Wiki"),
		"type": "source",
		"category": "Local",
		"in_type": "wikipage",
		"out_type": "wikipage"
	},
	"WikiPageConverter" : {
		"name": _("Wiki Converter"),
		"description": _("Bla"),
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": "",
	}
}

class MoinMoinDataSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("GNOME Wiki Source"), _("Get Pages from the GNOME Wiki"))
        self.icon_name = "applications-internet"
        
        #class specific
        self.srcwiki = None
        self.pagesString = ""
        self.pages = []
        
    def configure(self, window):
        def set_pages(param):
            self.pages = param.split(',')
            self.pagesString = param
        
        #Define the items in the configure dialogue
        items = [
                    {
                    "Name" : "Page Names to Synchronize:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_pages,
                    "InitialValue" : self.pagesString
                    }                    
                ]
        #We just use a simple configuration dialog
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        #This call blocks
        dialog.run()
        
    def refresh(self):
        if self.srcwiki is None:
            try:
                self.srcwiki = xmlrpclib.ServerProxy("http://live.gnome.org/?action=xmlrpc2")
            except:
                raise Exceptions.RefreshError
            
    def get(self):
        for p in self.pages:
            #Make a new page data type
            page = WikiPageDataType()
            pageinfo = self.srcwiki.getPageInfo(p)
            page.name = pageinfo["name"]
            page.modified = pageinfo["lastModified"]
            page.contents = self.srcwiki.getPage(p)
            
            yield page
		
class WikiPageDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, "wikipage")
                            
        #Instance variables
        self.contents = ""
        self.name = "" 
        self.modified = ""
        
class WikiPageConverter:
    def __init__(self):
        self.conversions =  {    
                            "wikipage,text"   : self.wikipage_to_text
                            }
                            

    def wikipage_to_text(self, page):
        return ("Wiki Page Name: %s\n\n%s" % (page.name,page.contents))
