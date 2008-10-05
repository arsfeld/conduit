import sys
import os
import tempfile
import datetime
import traceback
import logging
log = logging.getLogger("datatypes.File")

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
        
        #you can override the file implmentation at runtime
        #for testing purposes only
        implName = kwargs.get("implName", conduit.FILE_IMPL)
        if implName == "GnomeVfs":
            import conduit.platform.FileGnomeVfs as FileImpl
            self.FileImpl = FileImpl
        elif implName == "GIO":
            import conduit.platform.FileGio as FileImpl
            self.FileImpl = FileImpl
        elif implName == "Python":
            import conduit.platform.FilePython as FileImpl
            self.FileImpl = FileImpl
        else:
            raise Exception("File Implementation %s Not Supported" % implName)
            
        self._file = self.FileImpl.FileImpl(URI)
        
        #optional args
        self.basePath = kwargs.get("basepath","")
        self.group = kwargs.get("group","")

        #instance
        self._newFilename = None
        self._newMtime = None

        self._isProxyFile = False
        self._proxyFileSize = None
        
    def _close_file(self):
        self._file.close()

        #check to see if we have applied the rename/mtimes yet
        if self.get_filename() == self._newFilename:
            log.debug("Clearing pending rename")
            self._newFilename = None
        if self.get_mtime() == self._newMtime:
            log.debug("Clearing pending mtime")
            self._newMtime = None

    def _xfer_check_global_cancel_flag(self):
        return conduit.GLOBALS.cancelled

    def _get_text_uri(self):
        return self._file.get_text_uri()
            
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
        path = self._file.get_local_path()
        if self._file.is_local() and path and path.startswith(tmpdir):
            return True
        else:
            return False
            
    def _is_proxyfile(self):
        return self._isProxyFile

    def _set_file_mtime(self, mtime):
        timestamp = conduit.utils.datetime_get_timestamp(mtime)
        log.debug("Setting mtime of %s to %s (%s)" % (
                            self._file.get_text_uri(),
                            timestamp,
                            type(timestamp)))
        return self._file.set_mtime(timestamp)

    def _set_filename(self, filename):
        oldname = self._file.get_filename()
        olduri = self._file.get_text_uri()
        #ignore unicode for equality
        if str(filename) != str(oldname):
            newuri = self._file.set_filename(filename)
            if newuri:
                log.debug("Rename file %s (%s) -> %s (%s)" % (olduri,oldname,newuri,filename))
            else:
                log.debug("Error renaming file %s (%s) -> %s" % (olduri,oldname,filename))
            return newuri
        else:
            return olduri

    def set_from_instance(self, f):
        """
        Function to give this file all the properties of the
        supplied instance. This is important in converters where there
        might be pending renames etc on the file that you
        do not want to lose
        """
        self._file = f._file
        self.basePath = f.basePath
        self.group = f.group
        self._newFilename = f._newFilename
        self._newMtime = f._newMtime
        self._isProxyFile = f._isProxyFile
        self._proxyFileSize = f._proxyFileSize

    def to_tempfile(self):
        """
        Copies this file to a temporary file in the system tempdir
        @returns: The local file path
        """
        #Get a temporary file name
        tempname = tempfile.mkstemp(prefix="conduit")[1]
        log.debug("Tempfile %s -> %s" % (self._get_text_uri(), tempname))
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
        """
        Checks the file exists
        """        
        return self._file.exists()

    def is_local(self):
        """
        Checks if a File is on the local filesystem or not. If not, it is
        expected that the caller will call get_local_uri, which will
        copy the file to that location, and return the new path
        """
        return self._file.is_local()

    def is_directory(self):
        """
        @returns: True if the File is a directory
        """
        return self._file.is_directory()

    def make_directory(self):
        """
        Makes a directory with the default permissions.
        """
        return self._file.make_directory()

    def make_directory_and_parents(self):
        """
        Makes a directory and all parents up till the root. Equivilent
        to mkdir -p
        """
        return self._file.make_directory_and_parents()

    def force_new_filename(self, filename):
        """
        Renames the file
        """
        if self._is_tempfile() or self._is_proxyfile():
            self._defer_rename(filename)
        else:
            if not self._set_filename(filename):
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
        if self._is_tempfile() or self._is_proxyfile():
            self._defer_new_mtime(mtime)
        else:
            if not self._set_file_mtime(mtime):
                self._defer_new_mtime(mtime)

    def transfer(self, newURIString, overwrite=False, cancel_function=None):
        """
        Transfers the file to newURI. Returning True from 
        cancel_function gives the ability to cancel transfers

        @type newURIString: C{string}
        """
        trans = self.FileImpl.FileTransferImpl(
                                source=self._file,
                                dest=newURIString)
        
        #the default cancel function just checks conduit.GLOBALS.cancelled
        if cancel_function == None:
            cancel_function = self._xfer_check_global_cancel_flag

        if self._is_deferred_rename():
            log.debug("Using deferred filename in transfer")
            trans.set_destination_filename(self._newFilename)

        #transfer file
        ok,f = trans.transfer(overwrite, cancel_function)
        if not ok:
            raise FileTransferError

        #close the file and the handle so that the file info is refreshed
        self._file = f
        self._close_file()
        
        #if we have been transferred anywhere (i.e. the destination, our
        #location, is writable) then we are no longer a proxy file
        self._isProxyFile = False

        #apply any pending renames
        if self._is_deferred_rename():
            self.force_new_filename(self._newFilename)
        if self._is_deferred_new_mtime():
            self.force_new_mtime(self._newMtime)
      
    def delete(self):
        """
        Deletes the file
        """
        log.debug("Deleting %s" % self._file.get_text_uri())
        self._file.delete()

    def get_mimetype(self):
        """
        @returns: The file mimetype
        """
        return self._file.get_mimetype()
        
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
            ts = self._file.get_mtime()
            if ts:
                return datetime.datetime.fromtimestamp(ts)
            else:
                return None

    def set_mtime(self, mtime):
        """
        Sets the modification time of the file
        """
        if mtime != None:
            self.force_new_mtime(mtime)
    
    def get_size(self):
        """
        Gets the file size
        """
        if self._is_proxyfile():
            return self._proxyFileSize
        else:
            return self._file.get_size()

    def get_hash(self):
        # Join the tags into a string to be hashed so the object is updated if
        # they change.
        tagstr = "".join(self.get_tags())
        #FIXME: self.get_size() does not seem reliable
        return str(hash(tagstr))
                       
    def get_filename(self):
        """
        Returns the filename of the file
        """
        if self._is_deferred_rename():
            return self._newFilename
        else:
            return self._file.get_filename()

    def get_filename_and_extension(self):
        """
        @returns: filename,file_extension
        """
        return os.path.splitext(self.get_filename())

    def get_contents_as_text(self):
        return self._file.get_contents()
        
    def get_local_uri(self):
        """
        Gets the local URI (full path) for the file. If the file is 
        already on the local system then its local path is returned 
        (excluding the vfs sheme, i.e. file:///foo/bar becomes /foo/bar)
        
        If it is a remote file then a local temporary file copy is created
        
        @returns: local absolute path the the file or None on error
        @rtype: C{string}
        """
        path = self._file.get_local_path()
        if not path:
            return self.to_tempfile()
        else:
            return path
            
    def get_relative_uri(self):
        """
        @returns: The files URI relative to its basepath
        """
        if self.basePath:
            return Vfs.uri_get_relative(self.basePath,self._get_text_uri())
        else:
            return self._get_text_uri()

    def compare(self, B, sizeOnly=False):
        """
        Compare me with B based upon their modification times, or optionally
        based on size only
        """
        if B.exists() == False:
            return conduit.datatypes.COMPARISON_NEWER

        #Compare based on size only?
        if sizeOnly:
            meSize = self.get_size()
            bSize = B.get_size()
            log.debug("Comparing %s (SIZE: %s) with %s (SIZE: %s)" % (self._get_text_uri(), meSize, B._get_text_uri(), bSize))
            if meSize == None or bSize == None:
                return conduit.datatypes.COMPARISON_UNKNOWN
            elif meSize == bSize:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                return conduit.datatypes.COMPARISON_UNKNOWN

        #Else look at the modification times
        meTime = self.get_mtime()
        bTime = B.get_mtime()
        log.debug("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (self._get_text_uri(), meTime, B._get_text_uri(), bTime))
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

        implName = conduit.FILE_IMPL
        if implName == "GnomeVfs":
            import conduit.platform.FileGnomeVfs as FileImpl
        elif implName == "GIO":
            import conduit.platform.FileGio as FileImpl
        elif implName == "Python":
            import conduit.platform.FilePython as FileImpl
        else:
            raise Exception("File Implementation %s Not Supported" % implName)
        
        self._file = FileImpl.FileImpl(name)
        self.basePath = data['basePath']
        self.group = data['group']
        self._defer_rename(data['filename'])
        self._defer_new_mtime(data['filemtime'])

        DataType.DataType.__setstate__(self, data)

class TempFile(File):
    """
    Creates a file in the system temp directory with the given contents.
    """
    def __init__(self, contents, **kwargs):
        #create the file containing contents
        fd, name = tempfile.mkstemp(prefix="conduit")
        os.write(fd, contents)
        os.close(fd)
        File.__init__(self, name, **kwargs)
        log.debug("New tempfile created at %s" % name)
        
class ProxyFile(File):
    """
    Pretends to be a file for the sake of comparison and transfer. Typically
    located on a remote, read only resource, such as http://. Once transferred
    to the local filesystem, it behaves just like a file.
    """
    def __init__(self, URI, name, modified, size, **kwargs):
        File.__init__(self, URI, **kwargs)

        self._isProxyFile = True
        self._proxyFileSize = size
        
        if modified:
            self.force_new_mtime(modified)
        if name:
            self.force_new_filename(name)

            

