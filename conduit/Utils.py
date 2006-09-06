"""
Utility Functions

Part of this code copied from from Listen (c) 2006 Mehdi Abaakouk
(http://listengnome.free.fr/)

Copyright: John Stowers, 2006
License: GPLv2
"""

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
