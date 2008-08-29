import gio

import conduit.Vfs as Vfs
import conduit.platform

import logging
log = logging.getLogger("platform.FileGio")

class FileImpl(conduit.platform.File):
    SCHEMES = ("file://","http://","ftp://","smb://")
    def __init__(self, URI, impl=None):
        if impl:
            self._file = impl
        else:
            self._file = gio.File(URI)
        self.close()

    def _get_file_info(self):
        if not self.triedOpen:
            try:
                #FIXME: Only get attributes we actually care about
                self.fileInfo = self._file.query_info("standard::*,time::*")
                for ns in ("standard","time"):
                    log.info("%s Attributes: %s" % (
                            ns.title(),
                            ','.join(self.fileInfo.list_attributes(ns)))
                            )
                self.fileExists = True
            except gio.Error:
                self.fileExists = False
            self.triedOpen = True

    def get_text_uri(self):
        return self._file.get_uri()
        
    def get_local_path(self):
        return self._file.get_path()
        
    def is_local(self):
        return self._file.is_native()
        
    def is_directory(self):
        self._get_file_info()
        return self.fileInfo.get_file_type() == gio.FILE_TYPE_DIRECTORY
        
    def delete(self):
        #close the file and the handle so that the file info is refreshed
        self.close()
        try:
            #FIXME: Trash first?
            self._file.delete()
        except gio.Error, e:
            log.warn("File delete error: %s" % e)
        
    def exists(self):
        self._get_file_info()
        return self.fileExists
        
    def set_mtime(self, timestamp=None, datetime=None):
        try:
            self._file.set_attribute_uint64(
                        "time::changed",
                        long(timestamp)
                        )
            return timestamp
        except gio.Error:
            return None
        
    def set_filename(self, filename):
        try:
            self._file = self._file.set_display_name(filename)
            return filename
        except gio.Error:
            return None
        
    def get_mtime(self):
        self._get_file_info()
        mtime = self.fileInfo.get_attribute_uint64('time::modified')
        if mtime:
            return mtime
        else:
            #convert 0L -> None
            return None

    def get_filename(self):
        self._get_file_info()
        return self.fileInfo.get_display_name()
        
    def get_contents(self):
        return self._file.load_contents()
        
    def get_mimetype(self):
        self._get_file_info()
        return self.fileInfo.get_attribute_string('standard::content-type')

    def get_size(self):
        self._get_file_info()
        return self.fileInfo.get_size()

    def close(self):
        self.fileInfo = None
        self.fileExists = False
        self.triedOpen = False

class FileTransferImpl(conduit.platform.FileTransfer):
    def __init__(self, source, dest):
        self._source = source._file
        self._dest = gio.File(dest)
        self._cancel_func = lambda : False
        self._cancellable = gio.Cancellable()
        
    def _xfer_progress_callback(self, current, total):
        #check if cancelled
        try:
            if self._cancel_func():
                log.info("Transfer of %s -> %s cancelled" % (self._source.get_uri(), self._dest.get_uri()))
                c.cancel()
        except Exception:
            log.warn("Could not call gnomevfs cancel function")
        return True
        
    def set_destination_filename(self, name):
        #if it exists and its a directory then transfer into that dir
        #with the new filename
        try:
            info = self._dest.query_info("standard::name,standard::type")
            if info.get_file_type() == gio.FILE_TYPE_DIRECTORY:
                self._dest = self._dest.get_child(name)
        except gio.Error:
            #file does not exist
            pass

    def transfer(self, overwrite, cancel_func):
        self._cancel_func = cancel_func
    
        if overwrite:
            mode = gio.FILE_COPY_OVERWRITE
        else:
            mode = gio.FILE_COPY_NONE

        log.debug("Transfering File %s -> %s (overwrite: %s)" % (self._source.get_uri(), self._dest.get_uri(), overwrite))

        #recursively create all parent dirs if needed
        #http://bugzilla.gnome.org/show_bug.cgi?id=546575
        #
        #recursively create all parent dirs if needed
        #parent = str(self._dest.parent)
        #if not gnomevfs.exists(parent):
        #    d = FileImpl(None, impl=self._dest.parent)
        #    d.make_directory_and_parents()

        #Copy the file
        #http://bugzilla.gnome.org/show_bug.cgi?id=546601
        try:        
            ok = self._source.copy(
                        destination=self._dest,
                        flags=mode,
                        cancellable=self._cancellable,
                        progress_callback=self._xfer_progress_callback
                        )
            return True, FileImpl(None, impl=self._dest)
        except gio.Error, e:
            log.warn("File transfer error: %s" % e)
            return False, None

class VolumeMonitor(conduit.platform.VolumeMonitor):
    pass


