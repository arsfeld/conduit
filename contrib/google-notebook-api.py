#!/usr/bin/env python

__version__ = "0.1"
__date__ = "2006-05-16"
__author__ = "Poly9 Group (google-notebook-api@poly9.com)"
__url__ = "http://www.poly9.com/developers/gnotebook/google-notebook-api.pys"

import random, re, socket, time, urllib, urllib2
import sys
from Cookie import SimpleCookie


class GLoginFailure(Exception):
    pass

class GNotebookRefreshError(Exception):
    pass

# Once again, standing on the shoulders of rancidbacon, aka follower@myrealbox.com
class CookieJar:

    def __init__(self):
        self._cookies = {}

    def extractCookies(self, response, nameFilter = None):
        for cookie in response.headers.getheaders('Set-Cookie'):
            name, value = (cookie.split("=", 1) + [""])[:2]
            if not nameFilter or name in nameFilter:
                self._cookies[name] = value.split(";")[0]


    def addCookie(self, name, value):
        self._cookies[name] = value

    def hasCookie(self, name):
        return self._cookies.has_key(name)

    def setCookies(self, request):
        request.add_header('Cookie',
                           "; ".join(["%s=%s" % (k,v)
                                     for k,v in self._cookies.items()]))

       
class GHTTPCookieProcessor(urllib2.BaseHandler):
    def __init__(self, cookieJar):
        self.cookies = cookieJar
        
    def https_response(self, request, response):
        self.cookies.extractCookies(response)
        return response

    def https_request(self, request):
        self.cookies.setCookies(request)
        return request

GHTTPCookieProcessor.http_request = GHTTPCookieProcessor.https_request
GHTTPCookieProcessor.http_response = GHTTPCookieProcessor.https_response

class GService:
    """
        An abstract class to access Google various services. Useful to handle login and subsequent cookie dance.
    """
    def __init__(self):
        self._cookies = CookieJar()
        
    def login(self, username, password, service, serviceURL):
        """
        A login method which can be used to log to Google
        """
        p = self._get_page("https://www.google.com/accounts/ServiceLoginAuth",
            post_data="continue=%s&service=%s&nui=1&Email=%s&Passwd=%s&submit=null&PersistentCookie=yes&rmShown=1" % (self._url_quote(serviceURL), service, username, password))
        p.close()
        if not self._cookies.hasCookie('LSID'):
            raise GLoginFailure, "Could not login to %s" % (service)
        
    def _get_page(self, url, post_data=None):
        """
        Gets the url URL with cookies enabled. Posts post_data.
        """
        req = urllib2.build_opener(GHTTPCookieProcessor(self._cookies))
        f = req.open(self._encode(url), data=self._encode(post_data))
        
        if f.headers.dict.has_key('set-cookie'):
            self._cookies.extractCookies(f)
        return f

    def _url_quote(self, value): # This method is copyright (C) 2004, Adrian Holovaty
        """
        Helper method that quotes the given value for insertion into a query
        string. Also encodes into UTF-8, which Google uses, in case of
        non-ASCII characters.
        """
        value = self._encode(value)
        return urllib.quote_plus(value)

    def _encode(self, value): # This method is copyright (C) 2004, Adrian Holovaty
        """
        Helper method. Google uses UTF-8, so convert to it, in order to allow
        non-ASCII characters.
        """
        if isinstance(value, unicode):
            value = value.encode("utf-8")
        return value

class NotebookObj:
    """
    A minimalistic notebook container.
    """
    def __init__(self, *args):
        self.key = args[0]
        self.name = args[1]
        self.entries = args[7]

class NotebookEntry:
    """
    A minimalistic notebook entry container
    """
    def __init__(self, *args):
        self.key = args[0]
        self.content = args[1]
        
# This is a wrapper function that we use to get the notebook entries
def extractEntries(*args):
    return args[3]

# Some obfuscation bindings. May not work in the future
N = NotebookEntry
S = extractEntries
B = NotebookObj

class GNotebook(GService):
    """
    A very simple Google Notebook API
    """
    def __init__(self, username, password):
        GService.__init__(self)
        self.token = ""
        self.notebooks = {}
        self.username = username
        self.password = password
        if self.username and self.password:
            self.login(username, password)
            

    def login(self, username, password):
        """
        Logs to Google Notebook as username, get a Notebook token and retrieves a list of notebooks
        Raises a GLoginFailure exception if the login is unsuccessful
        """
        GService.login(self, username, password, "notebook", "http://google.com/notebook")
        self._getToken()
        self._refreshNotebooks()
        
    def _getToken(self):
        """
        Get a notebook token. Used in every GN requests
        """
        p = self._get_page("http://google.com/notebook/token?&pv=1.1&i=&tok=&cmd=")
        self.token = p.read().strip("/*").strip("*/")
        p.close()
        
    def _refreshNotebooks(self):
        """
        Private method that refreshes the list of notebooks (for internal use)
        """
        p = self._get_page("http://google.com/notebook/read?pv=1.1&i=&tok=%s&cmd=u&zx=%d" % (self.token, time.time()))
        r = p.read()
        p.close()
        r = r.strip("U(").replace(");", "")
        try:
            raw_notebooks = eval(r)
        except:
            raise GNotebookRefreshError, "Could not refresh the notebooks list."
        self.notebooks.clear()
        for n in raw_notebooks:
            self.notebooks[n.name] = n.key

    def _getNotebookID(self, notebook):
        """
        Private method. Returns the internal id used by GN to identify a Notebook.
        Raises a GNotebookNotFound exception if notebook's key is not found
        """
        if not self.notebooks.has_key(notebook):
            raise GNotebookNotFound, "Notebook %s was not found." % notebook
        return self.notebooks[notebook]
          
    def listNotebooks(self, forceRefresh=False):
        """
        Returns a list of notebooks. Set forceRefresh to True if you want to retrieve the list from the server.
        """
        if forceRefresh:
            self._refreshNotebooks()
        return self.notebooks.keys()

    def listNotebookEntries(self, notebook):
        """
        Returns a NotebookEntry list specific to notebook
        Raises a GNotebookNotFound exception if notebook is not found
        """
        nbid = self._getNotebookID(notebook)
        p = self._get_page("http://google.com/notebook/read?pv=1.1&i=&tok=%s&cmd=b&nbid=%s&zx=%d" % (self.token, nbid, time.time()))
        r = p.read().replace(";", "")
        p.close()
        try:
            raw_entries = eval(r)
            return raw_entries.entries[0]
        except:
           raise GNotebookRefresh, "Could not refresh %s entries" % notebook
        
    def addNote(self, notebook, content, url=""):
        """
        Adds a note to notebook which contains 'content' and may link to url
        """
        nbid = self._getNotebookID(notebook)
        p = self._get_page("http://google.com/notebook/write", "pv=1.1&i=&tok=%s&cmd=n&nbid=%s&contents=%s&qurl=%s" % (self.token, nbid, self._encode(content), self._encode(url)))
        p.close()
        
    def addNotebook(self, notebook):
        """
        Adds a notebook
        """
        p = self._get_page("http://google.com/notebook/write", "pv=1.1&i=&tok=%s&cmd=b&contents=%s" % (self.token, self._encode(notebook)))
        self._refreshNotebooks()

                           
if __name__ == "__main__":
    # Put your credentials here. Make sure that you are subscribed to Google Notebook
    username, password = "", ""
    try:
    	g = GNotebook(username, password)
    except:
        print "Could not log in to Google Notebook. Make sure your username and password are correct"
        sys.exit(1)
        
    print "The following notebooks are available"
    print "\n".join(g.listNotebooks())

    print "Creating a new notebook with a note"
    myNotebook = "my GNotebook"
    g.addNotebook(myNotebook)
    print "Adding a note to '%s'..." % myNotebook
    g.addNote(myNotebook, "Hello from GNotebook.py!", "http://poly9.com")
    for entry in g.listNotebookEntries(myNotebook):
        print entry.content
    
    myNotebook = random.choice(g.listNotebooks())
    print "Working on '%s'..." % myNotebook
    print "Entries in '%s':" % myNotebook
    i = 1
    for entry in g.listNotebookEntries(myNotebook):
        print "%d: %s" % (i, entry.content)
        i += 1
