import gio

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
                        "time::modified",
                        long(timestamp)
                        )
            self.close()
            return timestamp
        except gio.Error, e:
            return None
        
    def set_filename(self, filename):
        try:
            self._file = self._file.set_display_name(filename)
            self.close()
            return filename
        except gio.Error, e:
            return None
        
    def get_mtime(self):
        #FIXME: Workaround for 
        #http://bugzilla.gnome.org/show_bug.cgi?id=547133
        if self._file.get_uri_scheme() in ("http", "ftp"):
            from conduit.utils import get_http_resource_last_modified
            return get_http_resource_last_modified(self._file.get_uri())
        else:
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

    def get_uri_for_display(self):
        return self._file.get_parse_name()
        
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

    def make_directory(self):
        try:
            result = self._file.make_directory()
            self.close()
            return result
        except gio.Error, e:
            return False

    def make_directory_and_parents(self):
        #recursively create all parent dirs if needed
        #port the code from gio into python until the following is fixed
        #http://bugzilla.gnome.org/show_bug.cgi?id=546575
        dirs = []

        try:
            result = self._file.make_directory()
            code = 0;
        except gio.Error, e:
            result = False
            code = e.code

        work_file = self._file
        while code == gio.ERROR_NOT_FOUND and not result:
            parent_file = work_file.get_parent()
            if not parent_file:
                break

            try:
                result = parent_file.make_directory()
                code = 0;
            except gio.Error, e:
                result = False
                code = e.code

            if code == gio.ERROR_NOT_FOUND and not result:
                dirs.append(parent_file)

            work_file = parent_file;

        #make all dirs in reverse order
        dirs.reverse()
        for d in dirs:
            try:
                result = d.make_directory()
            except gio.Error:
                result = False
                break

        #make the final dir
        if result:
            try:
                result = self._file.make_directory()
            except gio.Error:
                result = False

        self.close()
        return result

    def is_on_removale_volume(self):
        try:
            return self._file.find_enclosing_mount().can_unmount()
        except gio.Error:
            return False

    def get_removable_volume_root_uri(self):
        try:
            return self._file.find_enclosing_mount().get_root().get_uri()
        except gio.Error:
            return None

    def get_filesystem_type(self):
        try:
            info = self._file.query_filesystem_info("filesystem::type")
            return info.get_attribute_string("filesystem::type")
        except gio.Error, e:
            return None

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
        parent = self._dest.get_parent()
        try:
            parent.query_info("standard::name")
        except gio.Error, e:
            #does not exists
            d = FileImpl(None, impl=parent)
            d.make_directory_and_parents()

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

class FileMonitor(conduit.platform.FileMonitor):
    pass

class FolderScanner(conduit.platform.FolderScanner):
    def run(self):
        delta = 0
        t = 1
        last_estimated = estimated = 0 
        while len(self.dirs)>0:
            if self.cancelled:
                return

            dir = self.dirs.pop(0)
            try: 
                f = gio.File(dir)
                enumerator = f.enumerate_children('standard::type,standard::name,standard::is-hidden,standard::is-symlink')
            except gio.Error:
                log.warn("Folder %s Not found" % dir)
                continue

            try: fileinfo = enumerator.next()
            except StopIteration: continue;
            while fileinfo:
                filename = fileinfo.get_name()
                filetype = fileinfo.get_file_type()
                hidden = fileinfo.get_is_hidden()
                if filename != self.CONFIG_FILE_NAME:
                    if filetype == gio.FILE_TYPE_DIRECTORY:
                        #Include hidden directories
                        if not hidden or self.includeHidden:
                            self.dirs.append(dir+"/"+filename)
                            t += 1
                    elif filetype == gio.FILE_TYPE_REGULAR or (filetype == gio.FILE_TYPE_SYMBOLIC_LINK and self.followSymlinks):
                            uri = dir+"/"+filename
                            #Include hidden files
                            if not hidden or self.includeHidden:
                                self.URIs.append(uri)
                    else:
                        log.debug("Unsupported file type: %s (%s)" % (filename, filetype))
                try: fileinfo = enumerator.next()
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
        log.debug("%s files loaded" % total)
        self.emit("scan-completed")

