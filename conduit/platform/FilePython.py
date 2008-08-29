import os.path
import mimetypes
import shutil

import conduit.platform

import logging
log = logging.getLogger("platform.FilePython")

class FileImpl(conduit.platform.File):
    SCHEMES = ("file://",)
    def __init__(self, URI):
        self._path = URI.split("file://")[-1]

    def get_text_uri(self):
        return self._path
        
    def get_local_path(self):
        return self._path
        
    def is_local(self):
        return True
        
    def is_directory(self):
        return os.path.isdir(self._path)
        
    def delete(self):
        os.unlink(self._path)
        
    def exists(self):
        os.path.exists(self._path)
        
    def set_mtime(self, timestamp=None, datetime=None):
        raise NotImplementedError        
        
    def set_filename(self, filename):
        raise NotImplementedError
        
    def get_mtime(self):
        raise NotImplementedError

    def get_filename(self):
        return os.path.basename(self._path)

    def get_uri_for_display(self):
        return self.get_filename()
        
    def get_contents(self):
        f = open(self._path, 'r')
        data = f.read()
        f.close()
        return data

    def get_mimetype(self):
        mimetype, encoding = mimetypes.guess_type(self._path)
        return mimetype
        
    def get_size(self):
        return os.path.getsize(self._path)

    def set_props(self, **props):
        pass
        
    def close(self):
        pass

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

class FileTransferImpl(conduit.platform.FileTransfer):
    pass

class VolumeMonitor(conduit.platform.VolumeMonitor):
    pass

class FileMonitor(conduit.platform.FileMonitor):
    pass

class FolderScanner(conduit.platform.FolderScanner):
    def run(self):
        self.emit("scan-completed")

