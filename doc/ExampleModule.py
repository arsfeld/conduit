"""
An Example DataSource and DataType implementation.

The most important field in this file is the MODULES dictionary. This
specifies the capabilities of the new DataSource and DataType and any 
conversion functions which have defined.

@var MODULES:  The MODULES variable is a dictionary of dictionaries. The
outer dict defines the name of a class defined in this file with the properties
specified by the value of the inner dict.

The keys in the inner dict represent
 -  name: The name of the DataProvider (for graphical purposes)
 -  description: Description of the DataProvider (for graphical purposes)
 -  type: String, "source" for Datasource, "sink" for Datasinks
    and "converter" for classes contating DataType conversion methods
 -  category: a DataProviderCategory object specifying a category name 
    and icon ("MoinMoin", "applications-internet" respecively)
 -  in_type: The name of the DataType this DataProvider accepts in its
    put() method (if present)
 -  out_type: The name of the DataType returned from this classes get()
    method

The dictionary is in the following format:::

    MODULES = {
    	"MoinMoinDataSource" : {
    		"name": _("GNOME Wiki Source"),
    		"description": _("Get Pages from the GNOME Wiki"),
    		"type": "source",
    		"category": DataProviderCategory("MoinMoin", "applications-internet"),
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

"""
import gtk
from gettext import gettext as _

import logging
import conduit
from conduit.DataProvider import DataSource, DataProviderCategory, DataProviderSimpleConfigurator
from conduit.datatypes import DataType
import conduit.Exceptions as Exceptions

import xmlrpclib

MODULES = {
	"MoinMoinDataSource" : {
		"name": _("GNOME Wiki Source"),
		"description": _("Get Pages from the GNOME Wiki"),
		"type": "source",
		"category": DataProviderCategory("MoinMoin", "applications-internet"),
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

class MoinMoinDataSource(DataSource):
    """
    This datasource fetches pages from the GNOME wiki.
    DataSources are presumed to be one-way, that is they are a source
    of data and should implement the get() and get_num_items() methods

    @ivar self.pages: A array of page names
    @type self.pages: C{string}[]
    """
    def __init__(self):
        """
        A DataSource constructor should call the base constructor with 
        three arguments
         1. The name of the datasource
         2. A short description
         3. An icon name
        The name and description are typically the same values as specified
        in the MODULES dict at the top of the file
        """
        DataSource.__init__(self, _("GNOME Wiki Source"), _("Get Pages from the GNOME Wiki"), "applications-internet")
        
        #class specific
        self.srcwiki = None
        self.pages = []
        
    def configure(self, window):
        """
        Uses the L{conduit.DataProvider.DataProviderSimpleConfigurator} class
        to show a simple configuration dialog which is just a gtk.Enry
        where the user can enter one or more GNOME wiki pages names,
        seperated by commas

        @param window: The parent window (used for modal dialogs)
        @type window: C{gtk.Window}
        """
        def set_pages(param):
            self.pages = param.split(',')
        
        #Make the list into a comma seperated string for display
        pageString = ",".join(self.pages)
        #Define the items in the configure dialogue
        items = [
                    {
                    "Name" : "Page Name to Synchronize:",
                    "Widget" : gtk.Entry,
                    "Callback" : set_pages,
                    "InitialValue" : pageString
                    }                    
                ]
        #We just use a simple configuration dialog
        dialog = DataProviderSimpleConfigurator(window, self.name, items)
        #This call blocks
        dialog.run()
        
    def refresh(self):
        """
        The refresh method should do whatever is needed to ensure that a 
        subseuent call to get_num_items returns the correct result.

        The refresh method is always called before the sync step. DataSources 
        should always call the base classes refresh() method
        """
        DataSource.refresh(self)
        if self.srcwiki is None:
            try:
                self.srcwiki = xmlrpclib.ServerProxy("http://live.gnome.org/?action=xmlrpc2")
            except:
                raise Exceptions.RefreshError

    def get_num_items(self):
        """
        Returns the number of items to synchronize. This number is used to
        determine how many times to call get().
        
        DataSources should always call the base classes get_num_items() method
        """
        DataSource.get_num_items(self)        
        return len(self.pages)
            
    def get(self, index):
        """
        Returns the data identified by the supplied index.

        The index will be in the range of 0 to the value returned from the
        previous call to get_num_items(). DataSources should always call 
        the base classes get() method.

        @param index: An index which uniquely represents data to return
        @type index: C{int}
        """
        DataSource.get(self, index)
        #Make a new page data type
        page = WikiPageDataType()
        #Get some meta-information atbout the page like date modified
        pageinfo = self.srcwiki.getPageInfo(self.pages[index])
        page.name = pageinfo["name"]
        page.modified = pageinfo["lastModified"]
        #Get the HTML page contents
        page.contents = self.srcwiki.getPage(self.pages[index])
        return page
            
    def get_configuration(self):
        """
        Returns a dict of key:value pairs. Key is the name of an internal
        variable, and value is its current value to save.

        It is important the the key is the actual name (minus the self.) of the
        internal variable that should be restored when the user saves
        their settings. 
        """
        return {"pages" : self.pages}
		
class WikiPageDataType(DataType.DataType):
    """
    A sample L{conduit.DataType.DataType} used to represent a page from
    the GNOME wiki.

    DataSources should try to used the supplied types (Note, File, etc) but
    if they must define their own then this class shows how. 

    @ivar self.contents: The raw HTML page contents
    @type self.contents: C{string}
    @ivar self.name: The page name
    @type self.name: C{string}
    @ivar self.modified: The date the page was modified
    @type self.modified: C{string}
    """
    def __init__(self):
        """
        Derived DataTypes should always call the base constructor 
        with a string represting the name of the new datatype.

        This name shoud should correspond to that specified in the MODULES dict
        """
        DataType.DataType.__init__(self, "wikipage")
                            
        #Instance variables
        self.contents = ""
        self.name = "" 
        self.modified = ""
        
class WikiPageConverter:
    """
    An example showing how to convert data from one type to another
    
    If you define your own DataType then you should define one or more
    converter (methods) for it, because it is likely that other DataSources, 
    such as the ones that ship with conduit will not know how to deal with
    the new DataType.

    The absolute minimum is to define a conversion to text as this will make
    one way sync with most datasinks possible. This conversion will generally
    lose information so in general it is better to define many conversion
    functions so that as much information is preserved when the data is
    passed to the sunsequent DataSink

    @ivar self.conversions: A dictionary mapping conversions to functions
    which perform the conversion
    """
    def __init__(self):
        """
        Fills out the required L{self.conversions} dict

        Simply provide a list of conversions and associated functions
        in the following formatt::
        
            self.conversions =  {    
                                "from_type_name,to_type_name" : convert_function
                                }
        """
        self.conversions =  {    
                            "wikipage,text"   : self.wikipage_to_text
                            }
                            

    def wikipage_to_text(self, page):
        """
        The conversion function for converting wikipages to raw text. Does
        not do anythong particuarly smart
        """
        return ("Wiki Page Name: %s\n\n%s" % (page.name,page.contents))
