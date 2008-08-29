import os.path
import logging
import gobject
import time
log = logging.getLogger("Vfs")

import conduit
import conduit.utils.Singleton as Singleton

if conduit.FILE_IMPL == "GnomeVfs":
    import conduit.platform.FileGnomeVfs as FileImpl
elif conduit.FILE_IMPL == "GIO":
    import conduit.platform.FileGio as FileImpl
elif conduit.FILE_IMPL == "Python":
    import conduit.platform.FilePython as FileImpl
else:
    raise Exception("File Implementation %s Not Supported" % conduit.FILE_IMPL)

VolumeMonitor   = FileImpl.VolumeMonitor
FileMonitor     = FileImpl.FileMonitor     
FolderScanner   = FileImpl.FolderScanner

def uri_is_valid(uri):
    """
    Checks if the uri is valid (i.e. not a local path), and its type
    is supported by the underlying file implementation
    """
    return uri[0] != "/" and uri.split("://")[0]+"://" in FileImpl.SCHEMES

def uri_join(first, *rest):
    """
    Joins multiple uri components. Performs safely if the first
    argument contains a uri scheme
    """
    first = conduit.utils.ensure_string(first)
    return os.path.join(first,*rest)

def uri_get_scheme(uri):
    """
    @returns: The scheme (file,smb,ftp) for the uri, or None on error
    """
    try:
        scheme,path = uri.split("://")
        return scheme
    except exceptions.ValueError:
        return None
    
def uri_get_relative(fromURI, toURI):
    """
    Returns the relative path fromURI --> toURI
    """
    fromURI = conduit.utils.ensure_string(fromURI)
    toURI = conduit.utils.ensure_string(toURI)
    rel = toURI.replace(fromURI,"")
    #strip leading /
    if rel[0] == os.sep:
        return rel[1:]
    else:
        return rel
    
def uri_open(uri):
    """
    Opens a xdg compatible uri.
    """
    uri = conduit.utils.ensure_string(uri)
    APP = "xdg-open"
    os.spawnlp(os.P_NOWAIT, APP, APP, uri)
    
def uri_to_local_path(uri):
    """
    @returns: The local path (/foo/bar) for the given URI
    """
    uri = conduit.utils.ensure_string(uri)
    scheme = uri_get_scheme(uri)
    if scheme == "file":
        #len("file://") = 7
        return a[7:]
    else:
        return None
    
def uri_get_volume_root_uri(uri):
    """
    @returns: The root path of the volume at the given uri, or None
    """
    f = FileImpl.FileImpl(uri)
    return f.get_removable_volume_root_uri()
    
def uri_is_on_removable_volume(uri):
    """
    @returns: True if the specified uri is on a removable volume, like a USB key
    or removable/mountable disk.
    """
    f = FileImpl.FileImpl(uri)
    return f.is_on_removale_volume()

def uri_get_filesystem_type(uri):
    """
    @returns: The filesystem that uri is stored on or None if it cannot
    be determined
    """
    f = FileImpl.FileImpl(uri)
    return f.get_filesystem_type()

def uri_escape(uri):
    """
    Escapes a uri, replacing only special characters that would not be found in 
    paths or host names.
    (so '/', '&', '=', ':' and '@' will not be escaped by this function)
    """
    import urllib
    uri = conduit.utils.ensure_string(uri)
    return urllib.quote(uri,safe='/&=:@')
    
def uri_unescape(uri):
    """
    Replace "%xx" escapes by their single-character equivalent.
    """
    import urllib
    uri = conduit.utils.ensure_string(uri)
    return urllib.unquote(uri)
    
def uri_get_protocol(uri):
    """
    Returns the protocol (file, smb, etc) for a URI
    """
    uri = conduit.utils.ensure_string(uri)
    if uri.rfind("://")==-1:
        return ""
    protocol = uri[:uri.index("://")+3]
    return protocol.lower()

def uri_get_filename(uri):
    """
    Method to return the filename of a file.
    """
    uri = conduit.utils.ensure_string(uri)
    return uri.split(os.sep)[-1]

def uri_get_filename_and_extension(uri):
    """
    Returns filename,file_extension
    """
    uri = conduit.utils.ensure_string(uri)
    return os.path.splitext(uri_get_filename(uri))
    
def uri_sanitize_for_filesystem(uri, filesystem=None):
    """
    Removes illegal characters in uri that cannot be stored on the 
    given filesystem - particuarly fat and ntfs types
    """
    uri = conduit.utils.ensure_string(uri)
    import string
    
    ILLEGAL_CHARS = {
        "vfat"  :   "\\:*?\"<>|",
        "ntfs"  :   "\\:*?\"<>|"
    }

    illegal = ILLEGAL_CHARS.get(filesystem,None)
    if illegal:
        #dont escape the scheme part
        idx = uri.rfind("://")
        if idx == -1:
            start = 0
        else:
            start = idx + 3        

        #replace illegal chars with a space, ignoring the scheme
        return uri[0:start]+uri[start:].translate(string.maketrans(
                                                illegal,
                                                " "*len(illegal)
                                                )
                                            )
    return uri
    
def uri_is_folder(uri):
    """
    @returns: True if the uri is a folder and not a file
    """
    f = FileImpl.FileImpl(uri)
    return f.is_directory()
    
def uri_format_for_display(uri):
    """
    Formats the uri so it can be displayed to the user (strips passwords, etc)
    """
    f = FileImpl.FileImpl(uri)
    return f.get_uri_for_display()
    
def uri_exists(uri):
    """
    @returns: True if the uri exists
    """
    f = FileImpl.FileImpl(uri)
    return f.exists()
        
class FolderScannerThreadManager:
    """
    Manages many FolderScanner threads. This involves joining and cancelling
    said threads, and respecting a maximum num of concurrent threads limit
    """
    def __init__(self, maxConcurrentThreads=2):
        self.maxConcurrentThreads = maxConcurrentThreads
        self.scanThreads = {}
        self.pendingScanThreadsURIs = []

    def make_thread(self, folderURI, includeHidden, followSymlinks, progressCb, completedCb, *args):
        """
        Makes a thread for scanning folderURI. The thread callsback the model
        at regular intervals with the supplied args
        """
        running = len(self.scanThreads) - len(self.pendingScanThreadsURIs)

        if folderURI not in self.scanThreads:
            thread = FolderScanner(folderURI, includeHidden, followSymlinks)
            thread.connect("scan-progress", progressCb, *args)
            thread.connect("scan-completed", completedCb, *args)
            thread.connect("scan-completed", self._register_thread_completed, folderURI)
            self.scanThreads[folderURI] = thread
            if running < self.maxConcurrentThreads:
                log.debug("Starting thread %s" % folderURI)
                self.scanThreads[folderURI].start()
            else:
                self.pendingScanThreadsURIs.append(folderURI)
            return thread
        else:
            return self.scanThreads[folderURI]

    def _register_thread_completed(self, sender, folderURI):
        """
        Decrements the count of concurrent threads and starts any 
        pending threads if there is space
        """
        #delete the old thread
        del(self.scanThreads[folderURI])
        running = len(self.scanThreads) - len(self.pendingScanThreadsURIs)

        log.debug("Thread %s completed. %s running, %s pending" % (folderURI, running, len(self.pendingScanThreadsURIs)))

        if running < self.maxConcurrentThreads:
            try:
                uri = self.pendingScanThreadsURIs.pop()
                log.debug("Starting pending thread %s" % uri)
                self.scanThreads[uri].start()
            except IndexError: pass

    def join_all_threads(self):
        """
        Joins all threads (blocks)

        Unfortunately we join all the threads do it in a loop to account
        for join() a non started thread failing. To compensate I time.sleep()
        to not smoke CPU
        """
        joinedThreads = 0
        while(joinedThreads < len(self.scanThreads)):
            for thread in self.scanThreads.values():
                try:
                    thread.join()
                    joinedThreads += 1
                except (RuntimeError, AssertionError):
                    #deal with not started threads
                    time.sleep(0.1)

    def cancel_all_threads(self):
        """
        Cancels all threads ASAP. My block for a small period of time
        because we use our own cancel method
        """
        for thread in self.scanThreads.values():
            if thread.isAlive():
                log.debug("Cancelling thread %s" % thread)
                thread.cancel()
            thread.join() #May block


