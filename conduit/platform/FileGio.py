import gio

import conduit.Vfs as Vfs
import conduit.platform

import logging
log = logging.getLogger("platform.FileGio")

class FileImpl(conduit.platform.File):
    SCHEMES = ("file://","http://","ftp://","smb://")
    def __init__(self, URI):
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
        except gio.Error:
            pass
        
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
        raise NotImplementedError

        self._source = source._URI
        self._dest = gnomevfs.URI(dest)
        self._cancel_func = lambda : False
        
    def _xfer_progress_callback(self, info):
        #check if cancelled
        try:
            if self._cancel_func():
                log.info("Transfer of %s -> %s cancelled" % (info.source_name, info.target_name))
                return 0
        except Exception, ex:
            log.warn("Could not call gnomevfs cancel function")
            return 0
        return True
        
    def set_destination_filename(self, name):
        #if it exists and its a directory then transfer into that dir
        #with the new filename
        if gnomevfs.exists(self._dest):
            info = gnomevfs.get_file_info(self._dest, gnomevfs.FILE_INFO_DEFAULT)
            if info.type == gnomevfs.FILE_TYPE_DIRECTORY:
                #append the new filename
                self._dest = self._dest.append_file_name(name)
        
    def transfer(self, overwrite, cancel_func):
        self._cancel_func = cancel_func
    
        if overwrite:
            mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
        else:
            mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP

        log.debug("Transfering File %s -> %s" % (self._source, self._dest))

        #recursively create all parent dirs if needed
        parent = str(self._dest.parent)
        if not gnomevfs.exists(parent):
            Vfs.uri_make_directory_and_parents(parent)

        #Copy the file
        try:        
            result = gnomevfs.xfer_uri(
                        source_uri=self._source,
                        target_uri=self._dest,
                        xfer_options=gnomevfs.XFER_NEW_UNIQUE_DIRECTORY,
                        error_mode=gnomevfs.XFER_ERROR_MODE_ABORT,
                        overwrite_mode=mode,
                        progress_callback=self._xfer_progress_callback
                        )
            #FIXME: Check error
            return True, FileImpl(str(self._dest))
        except gnomevfs.InterruptedError:
            return False, None
        except Exception, e:
            log.warn("File transfer error: %s" % e)
            return False, None
    
    
    


            

