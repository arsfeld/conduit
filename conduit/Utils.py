"""
Utility Functions

Part of this code copied from from Listen (c) 2006 Mehdi Abaakouk
(http://listengnome.free.fr/)

Copyright: John Stowers, 2006
License: GPLv2
"""
import sys
import os, os.path
import tempfile
import random
import md5
import gtk, gtk.glade
import gnomevfs
import socket
import datetime
import time
import urllib

from conduit import log,logd,logw
import conduit.datatypes.File as File

#Filename Manipulation
def get_protocol(uri):
    """
    Returns the gnome-vfs protocol (file, smb, etc) for a URI
    """
    if uri.rfind("://")==-1:
        return ""
    protocol = uri[:uri.index("://")+3]
    return protocol.lower()

def get_ext(uri,complete=True):
    """
    Returns the extension of a given URI
    """
    if uri.rfind(".")==-1:
        return ""
    if uri.rfind("#")!=-1:
        uri = uri[:uri.rindex("#")]
    if complete:
        return uri[uri.rindex("."):].lower()
    else:
        return uri[uri.rindex(".")+1:].lower()

def get_filename(path):
    """
    Method to return the filename of a file. Could use GnomeVFS for this
    is it wasnt so slow
    """
    return path.split(os.sep)[-1]

def new_tempfile(contents, contentsAreText=True):
    """
    Returns a new File onject, which has been created in the 
    system temporary directory, and that has been filled with
    contents
    
    The file is closed when it is returned
    
    @param contents: The data to write into the file
    @param contentsAreText: Indicates to the OS if the file is text (as opposed
    to a binary type file
    @param contentsAreText: C{bool}
    @returns: a L{conduit.datatypes.File}
    """
    return File.TempFile(contents)

def new_tempdir():
    """
    Creates a new temporary directory
    """
    return tempfile.mkdtemp("conduit")

def flatten_list(x):
    """flatten(sequence) -> list

    Returns a single, flat list which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).

    Examples:
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]
    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, MyVector(8,9,10)])
    [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]"""
    result = []
    for el in x:
        if hasattr(el, "__iter__"):
            result.extend(flatten_list(el))
        else:
            result.append(el)
    return result

def distinct_list(l):
    """
    Makes sure the items in l only appear once. l must be a 1D list of
    hashable items (i.e. not contain other lists)
    """
    return dict.fromkeys(l).keys()

def random_string(length=5):
    """
    returns a random string of length
    """
    s = ""
    for i in range(1,length):
        s += str(random.randint(0,10))
    return s

def dataprovider_add_dir_to_path(dataproviderfile, directory=""):
    """
    Adds directory to the python search path.

    From within a dataprovider (FooModule.py) 
    call with Utils.dataprovider_add_dir_to_path(__file__, some_dir):
    """
    path = os.path.join(dataproviderfile, "..", directory)
    path = os.path.abspath(path)
    logd("Adding %s to python path" % path)
    sys.path.insert(0,path)

def dataprovider_glade_get_widget(dataproviderfile, gladefilename, widget):
    path = os.path.join(dataproviderfile, "..", gladefilename)
    path = os.path.abspath(path)
    return gtk.glade.XML(path, widget)

def md5_string(string):
    """
    Returns the md5 of the supplied string in readable hexdigest string format
    """
    return md5.new(string).hexdigest()

def dbus_service_available(bus,interface):
    try: 
        import dbus
    except: 
        return False
    obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
    dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
    avail = dbus_iface.ListNames()
    return interface in avail

def get_user_string():
    """
    Makes a user and machine dependant string in the form
    username@hostname
    """
    hostname = socket.gethostname()
    username = os.environ.get("USER","")
    return "%s@%s" % (username, hostname)

def open_URI(uri):
    """
    Opens a gnomevfs or xdg compatible uri.
    FIXME: Use xdg-open?
    """
    if uri == None:
        logw("Cannot open non-existant URI")

    APP = "gnome-open"
    os.spawnlp(os.P_NOWAIT, APP, APP, uri)

def datetime_from_timestamp(t):
    """
    Makes a datetime object from a unix timestamp.

    Note: For the sake of consistancy always drop the
    fractional (microsecond) part of the timestamp
    """
    if type(t) not in [long, int, float]:
        raise Exception("Timestamp must be a number")

    if t < 0:
        raise Exception("Timestamps before 1970 are not valid")

    return datetime.datetime.fromtimestamp(long(t))

def datetime_get_timestamp(d):
    """
    Returns the unix timestamp for a datetime

    Note: For the sake of consistancy always drop the
    fractional (microsecond) part of the timestamp
    """
    if type(d) != datetime.datetime:
        raise Exception("Must supply a datetime")

    f = time.mktime(d.timetuple())

    if f < 0:
        raise Exception("Timestamps before 1970 are not valid")

    return long(f)

def escape(s):
    """
    Escapes a path or filename of special characters
    """
    return gnomevfs.escape_host_and_path_string(s)

def escape_html(s):
    """
    Escapes html special chars (&, <, >) for webservice dps
    """
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }
    L=[]
    for c in s:
        L.append(html_escape_table.get(c,c))
    return "".join(L)

def unescape(s):
    """
    Unescapes a quoted string presumably created by above
    """
    #the urllib implementation seems more reliable than gnomevfs.unescape
    return urllib.unquote(s)

class LoginTester:
    def __init__ (self, testFunc, timeout=30):
        self.testFunc = testFunc
        self.timeout = timeout

    def wait_for_login(self):
        start_time = time.time()

        while not self._is_timed_out(start_time):
            try:
                if self.testFunc():
                    return
            except Exception, e:
                logw("testFunc threw an error: %s" % e)
                pass

            time.sleep(2)

        raise Exception("Login timed out")

    def _is_timed_out(self, start):
        return int(time.time() - start) > self.timeout

