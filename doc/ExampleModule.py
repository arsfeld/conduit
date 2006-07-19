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
        
    def configure(self, mainwindow):
        dlg = gtk.Dialog(   "Enter the Wiki Page Names to Synchronize", 
                            mainwindow, 
                            0,
                            (gtk.STOCK_OK, gtk.RESPONSE_CLOSE)
                            )
        hbox = gtk.HBox(False,5)
        hbox.pack_start(gtk.Label("Page Names (Comma seperated):"))
        text = gtk.Entry()
        hbox.pack_start(text)
        dlg.vbox.pack_start(hbox)
        dlg.show_all()
        dlg.run()
        dlg.destroy()
        #Save the users choice
        self.pages = text.get_text().split(',')
        logging.debug("Configured pages = %s" % self.pages)
        
    def initialize(self):
        if self.srcwiki is None:
            self.srcwiki = xmlrpclib.ServerProxy("http://live.gnome.org/?action=xmlrpc2")
            
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
                            "email" : self.email_to_wikipage,
                            "cal"   : self.cal_to_wikipage
                            }
                            
        
    def email_to_wikipage(self, measure):
        return str(measure) + " was a email now is a wikipage"

    def cal_to_wikipage(self, measure):
        return str(measure) + " was a cal now is a wikipage"
