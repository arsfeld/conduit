import os.path
import shutil

import conduit.Vfs as Vfs
import conduit.platform

import logging
log = logging.getLogger("platform.FilePython")

class FileImpl(conduit.platform.File):
    SCHEMES = ("file://",)
    def __init__(self, URI):
        self._path = URI.split("file://")[-1]

class FileTransferImpl(conduit.platform.FileTransfer):
    pass

class VolumeMonitor(conduit.platform.VolumeMonitor):
    pass
