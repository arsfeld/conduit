import os
import tempfile
import datetime
import traceback
import gnomevfs

import conduit
from conduit import log,logd,logw
from conduit.datatypes import DataType

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
        
        #calculate the relative path
        self.relpath = self._get_text_uri().replace(self.basePath,"")

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
        logd("Closing file")
        self.fileInfo = None
        self.fileExists = False
        self.triedOpen = False

        #check to see if we have applied the rename/mtimes yet
        if self.get_filename() == self._newFilename:
            logd("Clearing pending rename")
            self._newFilename = None
        if self.get_mtime() == self._newMtime:
            logd("Clearing pending mtime")
            self._newMtime = None

    def _xfer_check_global_cancel_flag(self):
        return conduit.GLOBALS.cancelled

    def _xfer_progress_callback(self, info, cancel_func):
        #check if cancelled
        try:
            if cancel_func():
                log("Transfer of %s -> %s cancelled" % (info.source_name, info.target_name))
                return 0
        except Exception, ex:
            logw("Could not call gnomevfs cancel function")
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
                logw("Cannot get info on non-existant file %s" % self.URI)

    def _make_directory_and_parents(self, directory):
        """
        Because gnomevfs.make_dir does not perform as mkdir -p this function
        is required to make a heirarchy of directories.

        @param directory: A directory that does not exist
        @type directory: gnomevfs.URI
        """
        exists = False
        dirs = []
        while not exists:
            dirs.append(directory)
            directory = directory.parent
            exists = gnomevfs.exists(directory)

        dirs.reverse()
        for d in dirs:
            logd("Making directory %s" % d)
            gnomevfs.make_directory(
                d,
                gnomevfs.PERM_USER_ALL | gnomevfs.PERM_GROUP_READ | gnomevfs.PERM_GROUP_EXEC | gnomevfs.PERM_OTHER_READ | gnomevfs.PERM_OTHER_EXEC
                )

    def _defer_rename(self, filename):
        """
        In the event that the file is on a read-only volume this call defers the 
        file rename till after the transfer proces
        """
        logd("Defering rename till transfer (New name: %s)" % filename)
        self._newFilename = filename
        
    def _is_deferred_rename(self):
        return self._newFilename != None

    def _defer_new_mtime(self, mtime):
        """
        In the event that the file is on a read-only volume this call defers the 
        file mtime modification till after the transfer proces
        """
        logd("Defering new mtime till transfer (New mtime: %s)" % mtime)
        self._newMtime = mtime
        
    def _is_deferred_new_mtime(self):
        return self._newMtime != None
        
    def _is_tempfile(self):
        tmpdir = tempfile.gettempdir()
        if self.is_local() and self.URI.path.startswith(tmpdir):
            return True
        else:
            return False
            
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
        self.relpath = f.relpath
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
        logd("Tempfile %s -> %s" % (self.URI, tempname))
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
                newInfo = gnomevfs.FileInfo()
                newInfo.name = filename

                oldname = self.get_filename()
                olduri = self._get_text_uri()
                newuri = olduri.replace(oldname, filename)

                logd("Trying to rename file %s (%s) -> %s (%s)" % (olduri,oldname,newuri,filename))
                gnomevfs.set_file_info(self.URI,newInfo,gnomevfs.SET_FILE_INFO_NAME)

                #close so the file info is re-read
                self.URI = gnomevfs.URI(newuri)
                self._close_file()
            except gnomevfs.NotSupportedError:
                #dunno what this is
                self._defer_rename(filename)
            except gnomevfs.AccessDeniedError:
                #file is on readonly filesystem
                self._defer_rename(filename)
            except gnomevfs.NotPermittedError:
                #file is on readonly filesystem
                self._defer_rename(filename)
                
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
                timestamp = conduit.Utils.datetime_get_timestamp(mtime)
                logd("Setting mtime of %s to %s (%s)" % (self.URI, timestamp, type(timestamp)))
                newInfo = gnomevfs.FileInfo()
                newInfo.mtime = timestamp
                gnomevfs.set_file_info(self.URI,newInfo,gnomevfs.SET_FILE_INFO_TIME)
                #close so the file info is re-read
                self._close_file()
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
                    logd("Using deferred filename in transfer")
        else:
            newURI = gnomevfs.URI(newURIString)
            
        if overwrite:
            mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
        else:
            mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP
        
        logd("Transfering File %s -> %s" % (self.URI, newURI))

        #recursively create all parent dirs if needed
        parent = newURI.parent
        if not gnomevfs.exists(parent):
            self._make_directory_and_parents(parent)

        #Copy the file
        result = gnomevfs.xfer_uri(
                    source_uri=self.URI,
                    target_uri=newURI,
                    xfer_options=gnomevfs.XFER_NEW_UNIQUE_DIRECTORY,
                    error_mode=gnomevfs.XFER_ERROR_MODE_ABORT,
                    overwrite_mode=mode,
                    progress_callback=self._xfer_progress_callback,
                    data=cancel_function
                    )

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
        logd("Deleting %s" % self.URI)
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
                logw("Error setting mtime of %s. \n%s" % (self.URI, traceback.format_exc()))
    
    def get_size(self):
        """
        Gets the file size
        """
        self._get_file_info()
        try:
            return self.fileInfo.size
        except:
            return None
                       
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
            logd("Comparing %s (SIZE: %s) with %s (SIZE: %s)" % (self.URI, meSize, B.URI, bSize))
            if meSize == None or bSize == None:
                return conduit.datatypes.COMPARISON_UNKNOWN
            elif meSize == bSize:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                return conduit.datatypes.COMPARISON_UNKNOWN

        #Else look at the modification times
        meTime = self.get_mtime()
        bTime = B.get_mtime()
        logd("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (self.URI, meTime, B.URI, bTime))
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
            #logd("Comparing %s (SIZE: %s) with %s (SIZE: %s)" % (A.URI, meSize, B.URI, bSize))
            #If the times are equal, and the sizes are equal then assume
            #that they are the same.
            if meSize == None or bSize == None:
                #In case of error
                return conduit.datatypes.COMPARISON_UNKNOWN
            elif meSize == bSize:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                #shouldnt get here
                logw("Error comparing file sizes")
                return conduit.datatypes.COMPARISON_UNKNOWN
                
        else:
            logw("Error comparing file modification times")
            return conduit.datatypes.COMPARISON_UNKNOWN

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['uri'] = str(self.URI)
        data['basePath'] = self.basePath
        data['group'] = self.group
        data['data'] = open(self.get_local_uri(), 'rb').read()
        return data

    def __setstate__(self, data):
        fd, name = tempfile.mkstemp(prefix="netsync")
        os.write(fd, data['data'])
        os.close(fd)
        
        self.URI = gnomevfs.URI(data['uri'])
        self.basePath = data['basePath']
        self.group = data['group']
        self._defer_rename(name)

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
        logd("New tempfile created at %s" % name)

