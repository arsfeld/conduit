import os.path
import logging
log = logging.getLogger("Vfs")

try:
    import gnomevfs
except ImportError:
    from gnome import gnomevfs
    
#
# URI Functions
#
def uri_join(*args):
    """
    Joins multiple uri components
    """
    return os.path.join(*args)

def uri_open(uri):
    """
    Opens a gnomevfs or xdg compatible uri.
    """
    if uri == None:
        log.warn("Cannot open non-existant URI")

    #FIXME: Use xdg-open?
    APP = "gnome-open"
    os.spawnlp(os.P_NOWAIT, APP, APP, uri)
    
def uri_to_local_path(uri):
    """
    @returns: The local path (/foo/bar) for the given URI. Throws a 
    RuntimeError (wtf??) if the uri is not a local one    
    """
    return gnomevfs.get_local_path_from_uri(uri)
    
def uri_get_volume_root_uri(uri):
    """
    @returns: The root path of the volume at the given uri, or None
    """
    try:
        path = uri_to_local_path(uri)
        return VolumeMonitor().get_volume_for_path(path).get_activation_uri()
    except:
        return None
    
def uri_is_on_removable_volume(uri):
    """
    @returns: True if the specified uri is on a removable volume, like a USB key
    or removable/mountable disk.
    """
    scheme = gnomevfs.get_uri_scheme(uri)
    if scheme == "file":
        #FIXME: Unfortunately this approach actually works better than gnomevfs
        #return uri.startswith("file:///media/")
        try:
            path = uri_to_local_path(uri)
            return VolumeMonitor().get_volume_for_path(path).is_user_visible()
        except Exception, e:
            log.warn("Could not determine if uri on removable volume: %s" % uri)
            return False
    return False
    
    
def uri_get_filesystem_type(uri):
    """
    @returns: The filesystem that uri is stored on or None if it cannot
    be determined
    """
    scheme = gnomevfs.get_uri_scheme(uri)
    if scheme == "file":
        try:
            path = uri_to_local_path(uri)
            volume = VolumeMonitor().get_volume_for_path(path)
            return  volume.get_filesystem_type()
        except RuntimeError:
            log.warn("Could not get local path from URI")
            return None
        except AttributeError:
            log.warn("Could not determine volume for path")
            return None
    return None

def uri_make_canonical(uri):
    """
    Standardizes the format of the uri
    @param uri:an absolute or relative stringified uri. It might have scheme.
    """
    return gnomevfs.make_uri_canonical(uri)
    
def uri_escape(uri):
    """
    Escapes a uri, replacing only special characters that would not be found in 
    paths or host names.
    (so '/', '&', '=', ':' and '@' will not be escaped by this function)
    """
    #FIXME: This function lies, it escapes @
    #return gnomevfs.escape_host_and_path_string(uri)
    import urllib
    return urllib.quote(uri,safe='/&=:@')
    
def uri_unescape(uri):
    """
    Replace "%xx" escapes by their single-character equivalent.
    """
    import urllib
    return urllib.unquote(uri)
    
def uri_get_protocol(uri):
    """
    Returns the protocol (file, smb, etc) for a URI
    """
    if uri.rfind("://")==-1:
        return ""
    protocol = uri[:uri.index("://")+3]
    return protocol.lower()

def uri_get_filename(uri):
    """
    Method to return the filename of a file. Could use GnomeVFS for this
    is it wasnt so slow
    """
    return uri.split(os.sep)[-1]
    
def uri_sanitize_for_filesystem(uri, filesystem=None):
    """
    Removes illegal characters in uri that cannot be stored on the 
    given filesystem - particuarly fat and ntfs types
    """
    import string
    if filesystem in ("vfat","ntfs"):
        ILLEGAL_CHARS = "\\:*?\"<>|"
        #replace illegal chars with a space
        return uri.translate(string.maketrans(
                                ILLEGAL_CHARS,
                                " "*len(ILLEGAL_CHARS)))
    return uri
    
def uri_is_folder(uri):
    """
    @returns: True if the uri is a folder and not a file
    """
    info = gnomevfs.get_file_info(uri)
    return info.type == gnomevfs.FILE_TYPE_DIRECTORY
    
def uri_format_for_display(uri):
    """
    Formats the uri so it can be displayed to the user (strips passwords, etc)
    """
    return gnomevfs.format_uri_for_display(uri)
    
def uri_exists(uri):
    """
    @returns: True if the uri exists
    """
    try:
        return gnomevfs.exists(gnomevfs.URI(uri)) == 1
    except Exception, err:
        log.warn("Error checking if location exists")
        return False
        
def uri_make_directory(uri):
    """
    Makes a directory with the default permissions. Does not catch any
    error
    """
    gnomevfs.make_directory(
            uri,
            gnomevfs.PERM_USER_ALL | gnomevfs.PERM_GROUP_READ | gnomevfs.PERM_GROUP_EXEC | gnomevfs.PERM_OTHER_READ | gnomevfs.PERM_OTHER_EXEC
            )
        
def uri_make_directory_and_parents(uri):
    """
    Because gnomevfs.make_dir does not perform as mkdir -p this function
    is required to make a heirarchy of directories.

    @param uri: A directory that does not exist
    @type uri: str
    """
    exists = False
    dirs = []

    directory = gnomevfs.URI(uri)
    while not exists:
        dirs.append(directory)
        directory = directory.parent
        exists = gnomevfs.exists(directory)

    dirs.reverse()
    for d in dirs:
        log.debug("Making directory %s" % d)
        uri_make_directory(d)

#
# For monitoring locations
#
MONITOR_EVENT_CREATED =             gnomevfs.MONITOR_EVENT_CREATED
MONITOR_EVENT_CHANGED =             gnomevfs.MONITOR_EVENT_CHANGED
MONITOR_EVENT_DELETED =             gnomevfs.MONITOR_EVENT_DELETED
MONITOR_EVENT_METADATA_CHANGED =    gnomevfs.MONITOR_EVENT_METADATA_CHANGED
MONITOR_EVENT_STARTEXECUTING =      gnomevfs.MONITOR_EVENT_STARTEXECUTING
MONITOR_EVENT_STOPEXECUTING =       gnomevfs.MONITOR_EVENT_STOPEXECUTING
MONITOR_FILE =                      gnomevfs.MONITOR_FILE
MONITOR_DIRECTORY =                 gnomevfs.MONITOR_DIRECTORY

def monitor_add(folder, type, monitor_cb):
    try:
        return gnomevfs.monitor_add (folder, type, monitor_cb)
    except gnomevfs.NotSupportedError:
        # silently fail if we are looking at a folder that doesn't support directory monitoring
        return None

def monitor_cancel(monitor_id):
    gnomevfs.monitor_cancel(monitor_id)

class VolumeMonitor(gnomevfs.VolumeMonitor):
    pass

#
# Scanner ThreadManager
#
class FolderScannerThreadManager(object):
    """
    Manages many FolderScanner threads. This involves joining and cancelling
    said threads, and respecting a maximum num of concurrent threads limit
    """
    def __init__(self, maxConcurrentThreads=2):
        self.maxConcurrentThreads = maxConcurrentThreads
        self.scanThreads = {}
        self.pendingScanThreadsURIs = []

    def make_thread(self, folderURI, includeHidden, progressCb, completedCb, *args):
        """
        Makes a thread for scanning folderURI. The thread callsback the model
        at regular intervals with the supplied args
        """
        running = len(self.scanThreads) - len(self.pendingScanThreadsURIs)

        if folderURI not in self.scanThreads:
            thread = FolderScanner(folderURI, includeHidden)
            thread.connect("scan-progress",progressCb, *args)
            thread.connect("scan-completed",completedCb, *args)
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
                except AssertionError: 
                    #deal with not started threads
                    time.sleep(1)

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

#
# FOLDER SCANNER
#
import threading
import gobject
import time

CONFIG_FILE_NAME = ".conduit.conf"

class FolderScanner(threading.Thread, gobject.GObject):
    """
    Recursively scans a given folder URI, returning the number of
    contained files.
    """
    __gsignals__ =  { 
                    "scan-progress": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_INT]),
                    "scan-completed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    def __init__(self, baseURI, includeHidden):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.baseURI = str(baseURI)
        self.includeHidden = includeHidden

        self.dirs = [self.baseURI]
        self.cancelled = False
        self.URIs = []
        self.setName("FolderScanner Thread: %s" % self.baseURI)

    def run(self):
        """
        Recursively adds all files in dirs within the given list.
        
        Code adapted from Listen (c) 2006 Mehdi Abaakouk
        (http://listengnome.free.fr/)
        """
        delta = 0
        
        startTime = time.time()
        t = 1
        last_estimated = estimated = 0 
        while len(self.dirs)>0:
            if self.cancelled:
                return
            dir = self.dirs.pop(0)
            try:hdir = gnomevfs.DirectoryHandle(dir)
            except: 
                log.warn("Folder %s Not found" % dir)
                continue
            try: fileinfo = hdir.next()
            except StopIteration: continue;
            while fileinfo:
                filename = fileinfo.name
                if filename in [".","..",CONFIG_FILE_NAME]: 
                        pass
                else:
                    if fileinfo.type == gnomevfs.FILE_TYPE_DIRECTORY:
                        #Include hidden directories
                        if filename[0] != "." or self.includeHidden:
                            self.dirs.append(dir+"/"+filename)
                            t += 1
                    elif fileinfo.type == gnomevfs.FILE_TYPE_REGULAR:
                        try:
                            uri = uri_make_canonical(dir+"/"+filename)
                            #Include hidden files
                            if filename[0] != "." or self.includeHidden:
                                self.URIs.append(uri)
                        except UnicodeDecodeError:
                            raise "UnicodeDecodeError",uri
                    else:
                        log.debug("Unsupported file type: %s (%s)" % (filename, fileinfo.type))
                try: fileinfo = hdir.next()
                except StopIteration: break;
            #Calculate the estimated complete percentags
            estimated = 1.0-float(len(self.dirs))/float(t)
            estimated *= 100
            #Enly emit progress signals every 10% (+/- 1%) change to save CPU
            if delta+10 - estimated <= 1:
                log.debug("Folder scan %s%% complete" % estimated)
                self.emit("scan-progress", len(self.URIs))
                delta += 10
            last_estimated = estimated

        i = 0
        total = len(self.URIs)
        endTime = time.time()
        log.debug("%s files loaded in %s seconds" % (total, (endTime - startTime)))
        self.emit("scan-completed")

    def cancel(self):
        """
        Cancels the thread as soon as possible.
        """
        self.cancelled = True

    def get_uris(self):
        return self.URIs



