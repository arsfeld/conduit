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
import gnomevfs
import random

import logging
from conduit.datatypes import File


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

def do_gnomevfs_transfer(sourceURI, destURI, overwrite=False):
    """
    Xfers a file from fromURI to destURI. Overwrites if commanded.
    @raise Exception: if anything goes wrong in xfer
    """
    logging.debug("Transfering file from %s -> %s (Overwrite: %s)" % (sourceURI, destURI, overwrite))
    if overwrite:
        mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
    else:
        mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP
        
    #FIXME: I should probbably do something with the result returned
    #from xfer_uri
    result = gnomevfs.xfer_uri( sourceURI, destURI,
                                gnomevfs.XFER_DEFAULT,
                                gnomevfs.XFER_ERROR_MODE_ABORT,
                                mode)

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
    fd, name = tempfile.mkstemp(text=contentsAreText)
    os.write(fd, contents)
    os.close(fd)
    vfsFile = File.File(uri=name)
    return vfsFile

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

def dataprovider_add_dir_to_path(dataproviderfile, directory):
    """
    Adds directory to the python search path.

    From within a dataprovider (FooModule.py) 
    call with Utils.dataprovider_add_dir_to_path(__file__, some_dir):
    """
    path = os.path.join(dataproviderfile, "..", directory)
    path = os.path.abspath(path)
    logging.info("Adding %s to search path" % path)
    sys.path.insert(0,path)

def dataprovider_glade_get_widget(dataproviderfile, gladefilename, widget):
    import gtk, gtk.glade
    path = os.path.join(dataproviderfile, "..", gladefilename)
    path = os.path.abspath(path)
    return gtk.glade.XML(path, widget)

def md5_string(string):
    """
    Returns the md5 of the supplied string in readable hexdigest string format
    """
    return md5.new(string).hexdigest()


