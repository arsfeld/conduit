"""
Utility Functions

Part of this code copied from from Listen (c) 2006 Mehdi Abaakouk
(http://listengnome.free.fr/)

Copyright: John Stowers, 2006
License: GPLv2
"""
import os
import gnomevfs

import logging


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

