import os
import tempfile
import datetime
import time
import traceback
import gnomevfs

import conduit
from conduit import log,logd,logw
from conduit.datatypes import DataType

class File(DataType.DataType):
    def __init__(self, URI, **kwargs):
        DataType.DataType.__init__(self,"file")
        self._close_file()

        #optional args
        self.basePath = kwargs.get("basepath","")
        self.group = kwargs.get("group","")

        self.URI = gnomevfs.URI(URI)
        logd("Setting FILE open URI to %s" % URI)
        self.set_open_URI(URI)
        self.set_UID(URI)

    def _open_file(self):
        """
        Opens the file. 
        
        Only tries to do this once for performance reasons
        """
        if self.triedOpen == False:
            self.set_open_URI(self._get_text_uri())
            try:
                self.vfsFile = gnomevfs.Handle(self.URI)
                self.fileExists = True
                self.triedOpen = True
            except gnomevfs.NotFoundError:
                logd("Could not open file %s. Does not exist" % self.URI)
                self.fileExists = False
                self.triedOpen = True
            except:
                logd("Could not open file %s. Exception:\n%s" % (self.URI, traceback.format_exc()))
                self.fileExists = False
                self.triedOpen = True

    def _close_file(self):
        self.vfsHandle = None
        self.fileInfo = None
        self.triedOpen = False
        self.fileExists = False

    def _get_text_uri(self):
        """
        The mixing of text_uri and gnomevfs.URI in the gnomevfs api is very
        annoying. This function returns the full text uri for the file
        """
        return str(self.URI)        
            
    def _get_file_info(self):
        """
        Gets the file info. Because gnomevfs is dumb this method works a lot
        more reliably than self.vfsFile.get_file_info().
        
        Only tries to get the info once for performance reasons
        """
        #Open the file (if not already done so)
        self._open_file()
        #The get_file_info works more reliably on remote vfs shares
        if self.fileInfo == None:
            if self.fileExists == True:
                #self.fileInfo = self.vfsFile.get_file_info()
                #FIXME: HACK HACK Why does the following perform better on http?
                self.fileInfo = gnomevfs.get_file_info(self.URI, gnomevfs.FILE_INFO_DEFAULT)
            else:
                logw("Cannot get info on non-existant file %s" % self.URI)

    def exists(self):
        return gnomevfs.exists(self.URI)

    def is_local(self):
        """
        Checks if a File is on the local filesystem or not. If not, it is
        expected that the caller will call get_local_uri, which will
        copy the file to that location, and return the new path
        """
        return self.URI.is_local

    def force_new_filename(self, filename):
        """
        Renames the file
        """
        newInfo = gnomevfs.FileInfo()
        newInfo.name = filename

        oldname = self.get_filename()
        olduri = self._get_text_uri()
        newuri = olduri.replace(oldname, filename)

        logd("Renaming File %s -> %s" % (olduri, newuri))
        gnomevfs.set_file_info(self.URI,newInfo,gnomevfs.SET_FILE_INFO_NAME)

        #close so the file info is re-read
        self.URI = gnomevfs.URI(newuri)
        self._close_file()

    def force_new_mtime(self, mtime):
        """
        Changes the mtime of the file
        """
        timestamp = conduit.Utils.datetime_get_timestamp(mtime)
        logd("Setting mtime of %s to %s (%s)" % (self.URI, timestamp, type(timestamp)))
        newInfo = gnomevfs.FileInfo()
        newInfo.mtime = timestamp
        gnomevfs.set_file_info(self.URI,newInfo,gnomevfs.SET_FILE_INFO_TIME)
        #close so the file info is re-read
        self._close_file()

    def transfer(self, newURIString, overwrite=False):
        """
        Transfers the file to newURI. Thin wrapper around go_gnomevfs_transfer
        because it also sets the new info of the file.

        @type newURIString: C{string}
        """
        newURI = gnomevfs.URI(newURIString)

        if overwrite:
            mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
        else:
            mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP
        
        #FIXME: I should probbably do something with the result
        logd("Transfering File %s -> %s" % (self.URI, newURI))
        result = gnomevfs.xfer_uri( self.URI, newURI,
                                    gnomevfs.XFER_NEW_UNIQUE_DIRECTORY,
                                    gnomevfs.XFER_ERROR_MODE_ABORT,
                                    mode)

        #close the file and the handle so that the file info is refreshed
        self.URI = newURI
        self._close_file()

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
        self._get_file_info()
        return self.fileInfo.name
        
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
            #Get a temporary file name
            tempname = tempfile.mkstemp(prefix="conduit")[1]
            toURI = gnomevfs.URI(tempname)
            #Xfer to the temp file. 
            gnomevfs.xfer_uri( self.URI, toURI,
                               gnomevfs.XFER_DEFAULT,
                               gnomevfs.XFER_ERROR_MODE_ABORT,
                               gnomevfs.XFER_OVERWRITE_MODE_REPLACE)
            #now overwrite ourselves with the new local copy
            self._close_file()
            self.URI = toURI
            return tempname

    def compare(self, B, sizeOnly=False):
        """
        Compare me with B based upon their modification times, or optionally
        based on size only
        """
        if not gnomevfs.exists(B.URI):
            return conduit.datatypes.COMPARISON_NEWER

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
        #logd("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (self.URI, meTime, B.URI, bTime))
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

class TempFile(File):
    """
    A Small extension to a File. This allows new filenames (force_new_filename)
    to be processed in the transfer method, and not immediately, which may
    cause name conflicts in the temp directory. 

    USE VERY CAREFULLY
    """
    def __init__(self, contents):
        #create the file containing contents
        fd, name = tempfile.mkstemp(prefix="conduit")
        os.write(fd, contents)
        os.close(fd)

        File.__init__(self, name)

        self._newFilename = None
        logd("New tempfile created at %s" % name)
            
    def force_new_filename(self, filename):
        self._newFilename = filename

    def get_filename(self):
        if self._newFilename == None:
            return File.get_filename(self)
        else:
            return self._newFilename

    def transfer(self, newURIString, overwrite=False):
        if self._newFilename == None:
            File.transfer(self, newURIString, overwrite)
        else:
            URI = gnomevfs.URI(newURIString)
            #if it exists and its a directory then transfer into that dir
            #with the new filename
            if gnomevfs.exists(URI):
                info = gnomevfs.get_file_info(URI, gnomevfs.FILE_INFO_DEFAULT)
                if info.type == gnomevfs.FILE_TYPE_DIRECTORY:
                    #append the new filename
                    URI = URI.append_file_name(self._newFilename)

            logd("TempFile transferred to %s. filename %s" % (URI, self._newFilename))
            File.transfer(self, str(URI), overwrite)
          
