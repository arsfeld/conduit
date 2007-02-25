import os
import tempfile
import datetime
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
        self.set_open_URI(URI)

        #We can also override some parameters
        self._newInfo = gnomevfs.FileInfo()
        self._newInfoFlags = gnomevfs.SET_FILE_INFO_NONE

    def _open_file(self):
        """
        Opens the file. 
        
        Only tries to do this once for performance reasons
        """
        if self.triedOpen == False:
            #Otherwise try and get the file info
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
                self.fileInfo = self.vfsFile.get_file_info()#gnomevfs.get_file_info(self.URI, gnomevfs.FILE_INFO_DEFAULT)
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
        In the xfer process calling this method will cause the file to be
        copied with the newFilename.
       
        Useful if for some conversions a temp file is created that you dont
        want to retain the name of
        """
        self._newInfoFlags |= gnomevfs.SET_FILE_INFO_NAME
        self._newInfo.name = filename

    def force_new_mtime(self, mtime):
        """
        In the xfer process this will cause the new file to have the specified
        mtime
        """
        self._newInfoFlags |= gnomevfs.SET_FILE_INFO_TIME
        self._newInfo.mtime = mtime

    def transfer(self, newURI, overwrite=False):
        """
        Transfers the file to newURI. Thin wrapper around go_gnomevfs_transfer
        because it also sets the new info of the file.

        @type newURI: L{gnomevfs.URI}
        """
        if overwrite:
            mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
        else:
            mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP
        
        #FIXME: I should probbably do something with the result
        result = gnomevfs.xfer_uri( self.URI, newURI,
                                    gnomevfs.XFER_NEW_UNIQUE_DIRECTORY,
                                    gnomevfs.XFER_ERROR_MODE_ABORT,
                                    mode)

        #Now update file info
        if self._newInfoFlags != gnomevfs.SET_FILE_INFO_NONE:
            gnomevfs.set_file_info(newURI,self._newInfo,self._newInfoFlags)

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
            tempname = tempfile.mkstemp()[1]
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

    def compare(self, B):
        """
        Compare me with B based upon their modification times
        """
        if not gnomevfs.exists(B.URI):
            return conduit.datatypes.COMPARISON_MISSING

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

    def get_UID(self):
        """
        For a file the URI is a correct representation of the UID
        """
        return self._get_text_uri()

        
def TaggedFile(File):
    """
    A simple class to allow tags to be applied to files for those
    dataproviders that need this information (e.g. f-spot)
    """
    def __init__(self, URI, **kwargs):
        File.__init__(self, URI, **kwargs)
        DataType.DataType.__init__(self,"taggedfile")
        self.tags = []
    
    def set_tags(self, tags):
        self.tags = tags

    def get_tags(self):
        return self.tags
        
    def get_tag_string(self):
        return ",".join(self.tags)

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)
