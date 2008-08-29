import gobject

class File:

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
        
    def get_contents(self):
        raise NotImplementedError

    def get_mimetype(self):
        raise NotImplementedError
        
    def get_size(self):
        raise NotImplementedError

    def set_props(self, **props):
        pass
        
    def close(self):
        raise NotImplementedError
        
class FileTransfer:
    def __init__(self, source, dest):
        pass
        
    def set_destination_filename(self, name):
        raise NotImplementedError
        
    def transfer(self, cancel_func):
        raise NotImplementedError

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

