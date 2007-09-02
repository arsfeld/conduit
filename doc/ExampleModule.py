"""
An Example DataSource and DataType implementation.
"""
import gtk

import conduit
from conduit import log,logd,logw
from conduit.DataProvider import DataSource, DataProviderSimpleConfigurator, CATEGORY_FILES
from conduit.datatypes import DataType
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils

import xmlrpclib

MODULES = {
    "MoinMoinDataSource" :  { "type": "dataprovider" },
    "WikiPageConverter" :   { "type": "converter" }
}

class MoinMoinDataSource(DataSource):
    """
    This datasource fetches pages from the GNOME wiki.
    DataSources are presumed to be one-way, that is they are a source
    of data and should implement the get() and get_num_items() methods

    @ivar self.pages: A array of page names
    @type self.pages: C{string}[]
    """

    WIKI_ADDRESS = "http://live.gnome.org/"

    _name_ = "GNOME Wiki"
    _description_ = "Get Pages from the GNOME Wiki"
    _category_ = CATEGORY_FILES
    _module_type_ = "source"
    _in_type_ = "wikipage"
    _out_type_ = "wikipage"
    _icon_ = "applications-internet"

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
        DataSource.__init__(self)

        log("Hello World!")
        
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
        dialog = DataProviderSimpleConfigurator(window, self._name_, items)
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
                #use_datetime tells xmlrpc to return python datetime objects
                #for the page modification date
                self.srcwiki = xmlrpclib.ServerProxy(
                                            uri="http://live.gnome.org/?action=xmlrpc2",
                                            use_datetime=True
                                            )
            except:
                raise Exceptions.RefreshError

    def get_all(self):
        """
        Returns the LUIDs of all items to synchronize.        
        DataSources should always call the base classes get_all() method
        """
        DataSource.get_all(self)
        #the LUID for the page is its full url    
        return [MoinMoinDataSource.WIKI_ADDRESS+p for p in self.pages]
            
    def get(self, LUID):
        """
        Returns the data identified by the supplied LUID.
        @param LUID: A LUID which uniquely represents data to return
        @type LUID: C{str}
        """
        DataSource.get(self, LUID)

        #recover the page name from the full LUID string
        pagename = LUID.replace(MoinMoinDataSource.WIKI_ADDRESS,"")

        #get the page meta info, name, modified, etc
        pageinfo = self.srcwiki.getPageInfo(pagename)

        #Make a new page data type
        page = WikiPageDataType(
                            uri=LUID,
                            name=pageinfo["name"],
                            modified=pageinfo["lastModified"],
                            contents=self.srcwiki.getPage(pagename)
                            )

        #datatypes can be shared between modules. For this reason it is
        #always good to explicity set parameters like the LUID
        #even though in this case (we are the only one using the wikipage datatype)
        #they are set in the constructor of the dataype itself
        page.set_UID(LUID)
        page.set_open_URI(LUID)
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

    def get_UID(self):
        """
        @returns: A string uniquely representing this dataprovider.
        """
        return MoinMoinDataSource.WIKI_ADDRESS
        
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
    def __init__(self, uri, **kwargs):
        """
        Derived DataTypes should always call the base constructor 
        with a string represting the name of the new datatype.

        This name shoud should correspond to that specified in the MODULES dict
        """
        DataType.DataType.__init__(self, "wikipage")
                            
        #Instance variables
        self.contents = kwargs.get("contents","")
        self.name = kwargs.get("name", "")
        self.modified = kwargs.get("modified",None)

        #In the constructor of datatypes remember to call the following
        #base constructor functions. This allows certain information to be
        #preserved through conversions and comparison
        self.set_open_URI(uri)
        self.set_mtime(self.modified)

    def get_wikipage_string(self):
        """
        Returns the raw HTML for the page
        """
        return self.contents

    def get_wikipage_name(self):
        """
        Returns the page name
        """
        return self.name

    def __str__(self):
        """
        The result of str may be shown to the user. It should represent a
        small descriptive snippet of the Datatype. It does not necessarily need
        to be the entire raw textual representation of the data
        """
        return self.name
        
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
                            "wikipage,file"   : self.wikipage_to_file
                            }
                            

    def wikipage_to_file(self, page):
        """
        The conversion function for converting wikipages to raw text. Does
        not do anythong particuarly smart.
        """
        f = Utils.new_tempfile(
                        contents=page.get_wikipage_string()
                        )
        f.force_new_filename(page.get_wikipage_name())
        return f

