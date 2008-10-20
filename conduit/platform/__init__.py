import threading
import gobject

class File:
    SCHEMES = ()
    def __init__(self, URI):
        pass

    def get_text_uri(self):
        raise NotImplementedError
        
    def get_local_path(self):
        raise NotImplementedError
        
    def is_local(self):
        raise NotImplementedError
        
    def is_directory(self):
        raise NotImplementedError
        
    def delete(self):
        raise NotImplementedError
        
    def exists(self):
        raise NotImplementedError
        
    def set_mtime(self, timestamp=None, datetime=None):
        raise NotImplementedError        
        
    def set_filename(self, filename):
        raise NotImplementedError
        
    def get_mtime(self):
        raise NotImplementedError

    def get_filename(self):
        raise NotImplementedError

    def get_uri_for_display(self):
        raise NotImplementedError
        
    def get_contents(self):
        raise NotImplementedError

    def set_contents(self, contents):
        raise NotImplementedError

    def get_mimetype(self):
        raise NotImplementedError
        
    def get_size(self):
        raise NotImplementedError

    def set_props(self, **props):
        pass
        
    def close(self):
        raise NotImplementedError

    def make_directory(self):
        raise NotImplementedError

    def make_directory_and_parents(self):
        raise NotImplementedError

    def is_on_removale_volume(self):
        return False

    def get_removable_volume_root_uri(self):
        return None

    def get_filesystem_type(self):
        return None

    @staticmethod
    def uri_join(first, *rest):
        raise NotImplementedError

    @staticmethod
    def uri_get_relative(fromURI, toURI):
        raise NotImplementedError

    @staticmethod
    def uri_get_scheme(URI):
        raise NotImplementedError

class FileTransfer:
    def __init__(self, source, dest):
        pass
        
    def set_destination_filename(self, name):
        raise NotImplementedError
        
    def transfer(self, cancel_func):
        raise NotImplementedError

class VolumeMonitor(gobject.GObject):
    __gsignals__ = {
        "volume-mounted" :      (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING,        #udi/uuid
            gobject.TYPE_STRING,        #mount point
            gobject.TYPE_STRING]),      #label
        "volume-unmounted" :    (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING])       #udi/uuid

    }
    def __init__(self):
        gobject.GObject.__init__(self)

    def get_mounted_volumes(self):
        """
        @returs: Dict of mounted volumes, uuid : (mount, name) 
        """
        return {}

class FileMonitor(gobject.GObject):

    __gsignals__ = {
        "changed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT,
            gobject.TYPE_PYOBJECT,
            gobject.TYPE_PYOBJECT])
        }

    MONITOR_EVENT_CREATED = 1
    MONITOR_EVENT_CHANGED = 2
    MONITOR_EVENT_DELETED = 3
    MONITOR_DIRECTORY = 4

    def __init__(self):
        gobject.GObject.__init__(self)

    def add(self, folder, monitorType):
        pass
        
    def cancel(self):
        pass

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
    CONFIG_FILE_NAME = ".conduit.conf"
    def __init__(self, baseURI, includeHidden, followSymlinks):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.baseURI = str(baseURI)
        self.includeHidden = includeHidden
        self.followSymlinks = followSymlinks
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
        raise NotImplementedError

    def cancel(self):
        """
        Cancels the thread as soon as possible.
        """
        self.cancelled = True

    def get_uris(self):
        return self.URIs


class Settings:
    def __init__(self, defaults, changedCb):
        self._defaults = defaults
        self._changedCb = changedCb
        self._overrides = {}

    def get(self, key, **kwargs):
        return None

    def set(self, key, val, **kwargs):
        return False
        
    def set_overrides(self, **overrides):
        self._overrides = overrides
        
    def proxy_enabled(self):
        return False
        
    def get_proxy(self):
        return ("",0,"","")

    def save(self):
        pass
    
class WebBrowser(gobject.GObject):
    """
    Basic webbrowser abstraction to provide an upgrade path
    to webkit from gtkmozembed
    """
    __gsignals__ = {
        "location_changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING]),      # The new location
        "loading_started" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "loading_finished" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "loading_progress" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_FLOAT]),       # -1 (unknown), 0 -> 1 (finished)
        "status_changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING]),      # The status
        "open_uri": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING])       # URI
        }
    def __init__(self, emitOnIdle=False):
        gobject.GObject.__init__(self)
        self.emitOnIdle = emitOnIdle
        
    def emit(self, *args):
        """
        Override the gobject signal emission so that signals
        can be emitted from the main loop on an idle handler
        """
        if self.emitOnIdle == True:
            gobject.idle_add(gobject.GObject.emit,self,*args)
        else:
            gobject.GObject.emit(self,*args)

    def load_url(self, url):
        raise NotImplementedError

    def stop_load(self):
        raise NotImplementedError

