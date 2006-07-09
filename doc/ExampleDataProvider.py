import gtk
import gobject
from gettext import gettext as _
import xmlrpclib

import conduit
import DataProvider
import DataType

MODULES = {
	"MoinMoinDataProvider" : {
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

class MoinMoinDataProvider(DataProvider.DataProviderBase):
    def __init__(self):
        DataProvider.DataProviderBase.__init__(self, _("Wiki Source"), _("Moinmoin Wiki Source"))
        self.icon_name = "gtk-file"
        
        #class specific
        self.srcwiki = None
        self.pages = []
        
        #pages = [
        #        "Robots",
        #        "Nibbles",
        #        "Iagno"
        #        ]

        #for p in pages:
        #    pageinfo = srcwiki.getPageInfo(p)
        #    pagedata = srcwiki.getPage(p)
        #    print "Page Info: name=%s, modified=%s, author=%s, version=%s" % (
        #                                        pageinfo["name"], 
        #                                        pageinfo["lastModified"], 
        #                                        pageinfo["author"], pageinfo["version"]
        #                                        )
        
    def initialize(self):
        self.srcwiki = xmlrpclib.ServerProxy("http://live.gnome.org/?action=xmlrpc2")    
		
class WikiPageDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, _("Wiki Page Data Type"), _("Represents a Moinmoin wiki page"))
        self.conversions =  {    
                            "email" : self.email_to_wikipage,
                            "cal"   : self.cal_to_wikipage
                            }
                            
        
    def email_to_wikipage(self, measure):
        return str(measure) + " was a email now is a wikipage"

    def cal_to_wikipage(self, measure):
        return str(measure) + " was a cal now is a wikipage"
