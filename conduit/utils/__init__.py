"""
Utility Functions

Part of this code copied from from Listen (c) 2006 Mehdi Abaakouk
(http://listengnome.free.fr/)

Copyright: John Stowers, 2006
License: GPLv2
"""
import sys
import os.path
import socket
import datetime
import time
import re
import logging
log = logging.getLogger("Utils")

def get_proportional_resize(desiredW, desiredH, currentW, currentH):
    """
    Returns proportionally resized co-ordinates for an image
    """
    #Account for 'dont care about this axis sizing'
    if desiredH == None: desiredH = currentH
    if desiredW == None: desiredW = currentW

    #Calculate the axis of most change
    dw = abs(currentW - desiredW)
    dh = abs(currentH - desiredH)

    if dh > dw:
        newHeight = float(desiredH)
        percentage = newHeight / currentH
        newWidth = currentW * percentage
    else:
        newWidth = float(desiredW)
        percentage = newWidth / currentW
        newHeight = currentH * percentage

    return int(newWidth), int(newHeight)    
    
def program_installed(app):
    """
    Check if the given app is installed.
    """
    path = os.environ['PATH'] 
    paths = path.split(os.pathsep)
    for dir in paths:
        if os.path.isdir(dir):
            if os.path.isfile(os.path.join(dir,app)):
                return True
    return False

#
# Temporary file functions
#
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
    import conduit.datatypes.File as File
    return File.TempFile(contents)

def new_tempdir():
    """
    Creates a new temporary directory
    """
    import tempfile
    return tempfile.mkdtemp("conduit")

def unique_list(seq):
    """
    The fastes way to unique-ify a list while retaining its order, from
    http://www.peterbe.com/plog/uniqifiers-benchmark
    """
    def _f10(listy):
        seen = set()
        for x in listy:
            if x in seen:
                continue
            seen.add(x)
            yield x
    return list(_f10(seq))

def random_string(length=5):
    """
    returns a random string of length
    """
    import random
    s = ""
    for i in range(0,length):
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
    sys.path.insert(0,path)

def dataprovider_glade_get_widget(dataproviderfile, gladefilename, widget):
    """
    Gets a single gtk widget from a glad file
    """
    import gtk.glade
    path = os.path.join(dataproviderfile, "..", gladefilename)
    path = os.path.abspath(path)
    return gtk.glade.XML(path, widget)

def run_dialog(dialog, window=None):
    """
    Runs a given dialog, and makes it transient for
    the given window if any
    @param dialog: dialog 
    @param window: gtk window
    @returns: True if the user clicked OK to exit the dialog
    """
    import gtk

    if window:
        dialog.set_transient_for(window)

    return dialog.run() == gtk.RESPONSE_OK

def md5_string(string):
    """
    Returns the md5 of the supplied string in readable hexdigest string format
    """
    import md5
    return md5.new(string).hexdigest()

def uuid_string():
    """
    Returns a uuid string
    """
    try:
        import uuid
        return uuid.uuid4().hex
    except ImportError:
        import random, md5, socket
        t = long( time.time() * 1000 )
        r = long( random.random()*100000000000000000L )
        try:
            a = socket.gethostbyname( socket.gethostname() )
        except:
            a = random.random()*100000000000000000L
        data = str(t)+' '+str(r)+' '+str(a)
        data = md5.md5(data).hexdigest()
        return data

def dbus_service_available(interface, bus=None):
    """
    Checks if a dbus service is available on the given bus
    @param interface: The interface to look for
    @param bus: The bus to look on (optional)
    """
    try: 
        import dbus
    except: 
        return False
        
    if bus == None:        
        bus = dbus.SessionBus()
        
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

def encode_conversion_args(args):
    """
    encodes an args dictionary to a url string in the form
    param=value&param2=val2
    """
    import urllib
    return urllib.urlencode(args)

def decode_conversion_args(argString):
    """
    FIXME: dont import cgi for just one function. Also it doesnt
    even handle lists
    """
    import cgi
    args = {}
    for key,val in cgi.parse_qsl(argString):
        args[key] = val
    return args
    
def log_function_call(log):
    """
    A decorator that prints debug message showing the function name and
    argument types to the supplied logger instance. 
    
    Adapted from the accepts/returns decorators at
    http://wiki.python.org/moin/PythonDecoratorLibrary
    """
    def decorator(f):
        def newf(*args):
            #Ensure args are tuples with str args - necessart for CPython methods
            argtypes = map(str,map(type, args))
            argnames = map(str,f.func_code.co_varnames[:f.func_code.co_argcount])
            argnamesandtypes = ["%s:%s" % (i,j) for i,j in zip(argnames,argtypes)]
            msg = "Method Call %s(%s)" % (
                        f.__name__,
                        ', '.join(argnamesandtypes)
                        )
            log.debug(msg)
            return f(*args)
        #Retain information about old function
        newf.__name__ = f.__name__
        newf.__doc__ = f.__doc__
        newf.__dict__.update(f.__dict__)
        return newf
    return decorator

def xml_extract_value_from_tag(tag, text):
    """
    Returns the contents of the xml tag or None. Uses a simple regex.   

    Taken from:
    http://immike.net/blog/2007/04/06/5-regular-expressions-every-web-programmer-should-know/
    """
    ans = re.compile("<%(tag)s[^>]*>(.*?)</%(tag)s>" % {"tag":tag}).findall(text)
    if ans:
        return ans[0]
    else:
        return None
        
def get_module_information(module, versionAttributeName):
    """
    Prints the name, location and version of the supplied module
    """
    version = ""
    if versionAttributeName:
        try:
            version = " v%s" % str(getattr(module, versionAttributeName))
        except: pass
        
    path = ""
    try:
        path = " (%s)" % module.__file__
    except: pass
        
    return "%s%s%s" % (module.__name__, version, path)

