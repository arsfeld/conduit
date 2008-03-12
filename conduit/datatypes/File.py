import os
import tempfile
import datetime
import traceback
import logging
log = logging.getLogger("datatypes.File")

try:
    import gnomevfs
except ImportError:
    from gnome import gnomevfs # for maemo

import conduit
import conduit.datatypes.DataType as DataType
import conduit.Vfs as Vfs

class FileTransferError(Exception):
    pass

class File(DataType.DataType):
    
    _name_ = "file"

    def __init__(self, URI, **kwargs):
        """
        File constructor.
        Compulsory args
          - URI: The title of the note

        Optional kwargs
          - basepath: The files basepath
          - group: A named group to which this file belongs
        """
        DataType.DataType.__init__(self)
        #compulsory args
        self.URI = gnomevfs.URI(URI)

        #optional args
        self.basePath = kwargs.get("basepath","")
        self.group = kwargs.get("group","")

        #instance
        self.fileInfo = None
        self.fileExists = False
        self.triedOpen = False
        self._newFilename = None
        self._newMtime = None
        
    def _open_file(self):
        if self.triedOpen == False:
            self.triedOpen = True
            self.fileExists = gnomevfs.exists(self.URI)

    def _close_file(self):
        log.debug("Closing file")
        self.fileInfo = None
        self.fileExists = False
        self.triedOpen = False

        #check to see if we have applied the rename/mtimes yet
        if self.get_filename() == self._newFilename:
            log.debug("Clearing pending rename")
            self._newFilename = None
        if self.get_mtime() == self._newMtime:
            log.debug("Clearing pending mtime")
            self._newMtime = None

    def _xfer_check_global_cancel_flag(self):
        return conduit.GLOBALS.cancelled

    def _xfer_progress_callback(self, info, cancel_func):
        #check if cancelled
        try:
            if cancel_func():
                log.info("Transfer of %s -> %s cancelled" % (info.source_name, info.target_name))
                return 0
        except Exception, ex:
            log.warn("Could not call gnomevfs cancel function")
            return 0
        return True

    def _get_text_uri(self):
        """
        The mixing of text_uri and gnomevfs.URI in the gnomevfs api is very
        annoying. This function returns the full text uri for the file
        """
        return str(self.URI)        
            
    def _get_file_info(self):
        """
        Gets the file info. Because gnomevfs is dumb this method works a lot
        more reliably than self.vfsFileHandle.get_file_info().
        
        Only tries to get the info once for performance reasons
        """
        self._open_file()
        #The get_file_info works more reliably on remote vfs shares
        if self.fileInfo == None:
            if self.exists() == True:
                self.fileInfo = gnomevfs.get_file_info(self.URI, gnomevfs.FILE_INFO_DEFAULT)
            else:
                log.warn("Cannot get info on non-existant file %s" % self.URI)

    def _defer_rename(self, filename):
        """
        In the event that the file is on a read-only volume this call defers the 
        file rename till after the transfer proces
        """
        log.debug("Defering rename till transfer (New name: %s)" % filename)
        self._newFilename = filename
        
    def _is_deferred_rename(self):
        return self._newFilename != None

    def _defer_new_mtime(self, mtime):
        """
        In the event that the file is on a read-only volume this call defers the 
        file mtime modification till after the transfer proces
        """
        log.debug("Defering new mtime till transfer (New mtime: %s)" % mtime)
        self._newMtime = mtime
        
    def _is_deferred_new_mtime(self):
        return self._newMtime != None
        
    def _is_tempfile(self):
        tmpdir = tempfile.gettempdir()
        if self.is_local() and self.URI.path.startswith(tmpdir):
            return True
        else:
            return False

    def _set_file_mtime(self, mtime):
        timestamp = conduit.Utils.datetime_get_timestamp(mtime)
        log.debug("Setting mtime of %s to %s (%s)" % (self.URI, timestamp, type(timestamp)))
        newInfo = gnomevfs.FileInfo()
        newInfo.mtime = timestamp
        gnomevfs.set_file_info(self.URI,newInfo,gnomevfs.SET_FILE_INFO_TIME)
        #close so the file info is re-read
        self._close_file()

    def _set_filename(self, filename):
        newInfo = gnomevfs.FileInfo()
        
        #FIXME: Gnomevfs complains if name is unicode
        filename =  str(filename)
        oldname =   str(self.get_filename())

        if filename != oldname:
            newInfo.name = filename
            olduri = self._get_text_uri()
            newuri = olduri.replace(oldname, filename)

            log.debug("Trying to rename file %s (%s) -> %s (%s)" % (olduri,oldname,newuri,filename))
            gnomevfs.set_file_info(self.URI,newInfo,gnomevfs.SET_FILE_INFO_NAME)
            #close so the file info is re-read
            self.URI = gnomevfs.URI(newuri)
            self._close_file()
            
    def set_from_instance(self, f):
        """
        Function to give this file all the properties of the
        supplied instance. This is important in converters where there
        might be pending renames etc on the file that you
        do not want to lose
        """
        self.URI = f.URI
        self.basePath = f.basePath
        self.group = f.group
        self.fileInfo = f.fileInfo
        self.fileExists = f.fileExists
        self.triedOpen = f.triedOpen
        self._newFilename = f._newFilename
        self._newMtime = f._newMtime

    def to_tempfile(self):
        """
        Copies this file to a temporary file in the system tempdir
        @returns: The local file path
        """
        #Get a temporary file name
        tempname = tempfile.mkstemp(prefix="conduit")[1]
        log.debug("Tempfile %s -> %s" % (self.URI, tempname))
        filename = self.get_filename()
        mtime = self.get_mtime()
        self.transfer(
                newURIString=tempname,
                overwrite=True
                )
        #retain all original information
        self.force_new_filename(filename)
        self.force_new_mtime(mtime)
        return tempname

    def exists(self):
        self._open_file()
        return self.fileExists

    def is_local(self):
        """
        Checks if a File is on the local filesystem or not. If not, it is
        expected that the caller will call get_local_uri, which will
        copy the file to that location, and return the new path
        """
        return self.URI.is_local

    def is_directory(self):
        """
        @returns: True if the File is a directory
        """
        self._get_file_info()
        return self.fileInfo.type == gnomevfs.FILE_TYPE_DIRECTORY

    def force_new_filename(self, filename):
        """
        Renames the file
        """
        if self._is_tempfile():
            self._defer_rename(filename)
        else:
            try:
                self._set_filename(filename)
            except gnomevfs.NotSupportedError:
                #dunno what this is
                self._defer_rename(filename)
            except gnomevfs.AccessDeniedError:
                #file is on readonly filesystem
                self._defer_rename(filename)
            except gnomevfs.NotPermittedError:
                #file is on readonly filesystem
                self._defer_rename(filename)
            except gnomevfs.FileExistsError:
                #I think this is when you rename a file to its current name
                pass
                
    def force_new_file_extension(self, ext):
        """
        Changes the file extension to ext. 
        @param ext: The new file extension (including the dot)
        """
        curname,curext = self.get_filename_and_extension()
        if curext != ext:
            self.force_new_filename(curname+ext)

    def force_new_mtime(self, mtime):
        """
        Changes the mtime of the file
        """
        if self._is_tempfile():
            self._defer_new_mtime(mtime)
        else:
            try:
                self._set_file_mtime(mtime)
            except gnomevfs.NotSupportedError:
                #dunno what this is
                self._defer_new_mtime(mtime)
            except gnomevfs.AccessDeniedError:
                #file is on readonly filesystem
                self._defer_new_mtime(mtime)
            except gnomevfs.NotPermittedError:
                #file is on readonly filesystem
                self._defer_new_mtime(mtime)

    def transfer(self, newURIString, overwrite=False, cancel_function=None):
        """
        Transfers the file to newURI. Thin wrapper around go_gnomevfs_transfer
        because it also sets the new info of the file. By wrapping the xfer_uri
        funtion it gives the ability to cancel transfers

        @type newURIString: C{string}
        """
        #the default cancel function just checks conduit.GLOBALS.cancelled
        if cancel_function == None:
            cancel_function = self._xfer_check_global_cancel_flag

        if self._is_deferred_rename():
            newURI = gnomevfs.URI(newURIString)
            #if it exists and its a directory then transfer into that dir
            #with the new filename
            if gnomevfs.exists(newURI):
                info = gnomevfs.get_file_info(newURI, gnomevfs.FILE_INFO_DEFAULT)
                if info.type == gnomevfs.FILE_TYPE_DIRECTORY:
                    #append the new filename
                    newURI = newURI.append_file_name(self._newFilename)
                    log.debug("Using deferred filename in transfer")
        else:
            newURI = gnomevfs.URI(newURIString)
            
        if overwrite:
            mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
        else:
            mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP
        
        log.debug("Transfering File %s -> %s" % (self.URI, newURI))

        #recursively create all parent dirs if needed
        parent = str(newURI.parent)
        if not gnomevfs.exists(parent):
            Vfs.uri_make_directory_and_parents(parent)

        #Copy the file
        try:        
            result = gnomevfs.xfer_uri(
                        source_uri=self.URI,
                        target_uri=newURI,
                        xfer_options=gnomevfs.XFER_NEW_UNIQUE_DIRECTORY,
                        error_mode=gnomevfs.XFER_ERROR_MODE_ABORT,
                        overwrite_mode=mode,
                        progress_callback=self._xfer_progress_callback,
                        data=cancel_function
                        )
        except gnomevfs.InterruptedError:
            raise FileTransferError

        #close the file and the handle so that the file info is refreshed
        self.URI = newURI
        self._close_file()

        #apply any pending renames
        if self._is_deferred_rename():
            self.force_new_filename(self._newFilename)
        if self._is_deferred_new_mtime():
            self.force_new_mtime(self._newMtime)
      
    def delete(self):
        #close the file and the handle so that the file info is refreshed
        self._close_file()
        log.debug("Deleting %s" % self.URI)
        result = gnomevfs.unlink(self.URI)

    def get_mimetype(self):
        self._get_file_info()
        try:
            return self.fileInfo.mime_type
        except ValueError:
            #Why is gnomevfs so stupid and must I do this for local URIs??
            return gnomevfs.get_mime_type(self._get_text_uri())
        
    def get_mtime(self):
        """
        Returns the modification time for the file
        
        @returns: A python datetime object containing the modification time
        of the file or None on error.
        @rtype: C{datetime}
        """
        if self._is_deferred_new_mtime():
            return self._newMtime
        else:
            self._get_file_info()
            try:
                return datetime.datetime.fromtimestamp(self.fileInfo.mtime)
            except:
                return None

    def set_mtime(self, mtime):
        """
        Sets the modification time of the file
        """
        if mtime != None:
            try:
                self.force_new_mtime(mtime)
            except Exception, err:
                log.warn("Error setting mtime of %s. \n%s" % (self.URI, traceback.format_exc()))
    
    def get_size(self):
        """
        Gets the file size
        """
        self._get_file_info()
        try:
            return self.fileInfo.size
        except:
            return None

    def get_hash(self):
        #FIXME: self.get_size() does not seem reliable
        return hash(None)
                       
    def get_filename(self):
        """
        Returns the filename of the file
        """
        if self._is_deferred_rename():
            return self._newFilename
        else:
            self._get_file_info()
            return self.fileInfo.name

    def get_filename_and_extension(self):
        """
        @returns: filename,file_extension
        """
        return os.path.splitext(self.get_filename())

    def get_contents_as_text(self):
        return gnomevfs.read_entire_file(self._get_text_uri())
        
    def get_local_uri(self):
        """
        Gets the local URI (full path) for the file. If the file is 
        already on the local system then its local path is returned 
        (excluding the vfs sheme, i.e. file:///foo/bar becomes /foo/bar)
        
        If it is a remote file then a local temporary file copy is created
        
        This function is useful for non gnomevfs enabled libs

        @returns: local absolute path the the file or None on error
        @rtype: C{string}
        """
        if self.is_local():
            #FIXME: The following call produces a runtime error if the URI
            #is malformed. Reason number 37 gnomevfs should die
            u = gnomevfs.get_local_path_from_uri(self._get_text_uri())
            #Backup approach...
            #u = self.URI[len("file://"):]
            return u
        else:
            return self.to_tempfile()
            
    def get_relative_uri(self):
        """
        @returns: The files URI relative to its basepath
        """
        return self._get_text_uri().replace(self.basePath,"")

    def compare(self, B, sizeOnly=False, existOnly=False):
        """
        Compare me with B based upon their modification times, or optionally
        based on size only
        """
        if not gnomevfs.exists(B.URI):
            return conduit.datatypes.COMPARISON_NEWER
        else:
            if existOnly:
                return conduit.datatypes.COMPARISON_OLDER

        #Compare based on size only?
        if sizeOnly:
            meSize = self.get_size()
            bSize = B.get_size()
            log.debug("Comparing %s (SIZE: %s) with %s (SIZE: %s)" % (self.URI, meSize, B.URI, bSize))
            if meSize == None or bSize == None:
                return conduit.datatypes.COMPARISON_UNKNOWN
            elif meSize == bSize:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                return conduit.datatypes.COMPARISON_UNKNOWN

        #Else look at the modification times
        meTime = self.get_mtime()
        bTime = B.get_mtime()
        log.debug("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (self.URI, meTime, B.URI, bTime))
        if meTime is None:
            return conduit.datatypes.COMPARISON_UNKNOWN
        if bTime is None:            
            return conduit.datatypes.COMPARISON_UNKNOWN
        
        #Am I newer than B
        if meTime > bTime:
            return conduit.datatypes.COMPARISON_NEWER
        #Am I older than B?
        elif meTime < bTime:
            return conduit.datatypes.COMPARISON_OLDER

        elif meTime == bTime:
            meSize = self.get_size()
            bSize = B.get_size()
            #log.debug("Comparing %s (SIZE: %s) with %s (SIZE: %s)" % (A.URI, meSize, B.URI, bSize))
            #If the times are equal, and the sizes are equal then assume
            #that they are the same.
            if meSize == None or bSize == None:
                #In case of error
                return conduit.datatypes.COMPARISON_UNKNOWN
            elif meSize == bSize:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                #shouldnt get here
                log.warn("Error comparing file sizes")
                return conduit.datatypes.COMPARISON_UNKNOWN
                
        else:
            log.warn("Error comparing file modification times")
            return conduit.datatypes.COMPARISON_UNKNOWN

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['basePath'] = self.basePath
        data['group'] = self.group
        data['filename'] = self.get_filename()
        data['filemtime'] = self.get_mtime()

        #FIXME: Maybe we should tar this first...
        data['data'] = open(self.get_local_uri(), 'rb').read()

        return data

    def __setstate__(self, data):
        fd, name = tempfile.mkstemp(prefix="netsync")
        os.write(fd, data['data'])
        os.close(fd)
        
        self.URI = gnomevfs.URI(name)
        self.basePath = data['basePath']
        self.group = data['group']
        self._defer_rename(data['filename'])
        self._defer_new_mtime(data['filemtime'])

        #Ensure we re-read the fileInfo
        self.fileInfo = None
        self.fileExists = False
        self.triedOpen = False
        
        DataType.DataType.__setstate__(self, data)

class TempFile(File):
    """
    A Small extension to a File. This makes new filenames (force_new_filename)
    to be processed in the transfer method, and not immediately, which may
    cause name conflicts in the temp directory. 
    """
    def __init__(self, contents=""):
        #create the file containing contents
        fd, name = tempfile.mkstemp(prefix="conduit")
        os.write(fd, contents)
        os.close(fd)
        File.__init__(self, name)
        log.debug("New tempfile created at %s" % name)

