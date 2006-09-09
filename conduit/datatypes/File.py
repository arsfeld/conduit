import gnomevfs
import conduit
import logging
from conduit.datatypes import DataType

import os
import tempfile
import datetime
import traceback

def new_from_tempfile(contents, contentsAreText=True):
    """
    Returns a new File onject, which has been created in the 
    system temporary directory, and that has been filled with
    contents
    
    The file is closed when it is returned
    
    @param contents: The data to write into the file
    @param contentsAreText: Indicates to the OS if the file is text (as opposed
    to a binary type file
    @param contentsAreText: C{bool}
    """
    fd, name = tempfile.mkstemp(text=contentsAreText)
    os.write(fd, contents)
    os.close(fd)
    vfsFile = File(name)
    return vfsFile
    
class File(DataType.DataType):
    def __init__(self, uriString=None):
        DataType.DataType.__init__(self,"file")

        self.URI = uriString            
        self.vfsHandle = None
        self.fileInfo = None
        self.forceNewFilename = ""
        self.triedOpen = False
        self.fileExists = False
        
    def _open_file(self):
        """
        Opens the file. 
        
        Only tries to do this once for performance reasons
        """
        if self.triedOpen == False:
            #Catches the case of a file which is used only as a temp
            #file, like in some dataproviders
            if self.URI == None:
                self.fileExists = False
                self.triedOpen = True
                return
                
            #Otherwise try and get the file info
            try:
                self.vfsFile = gnomevfs.Handle(self.URI)
                self.fileExists = True
                self.triedOpen = True
            except gnomevfs.NotFoundError:
                logging.debug("Could not open file %s. Does not exist" % self.URI)
                self.fileExists = False
                self.triedOpen = True
            except:
                logging.debug("Could not open file %s. Exception:\n%s" % (self.URI, traceback.format_exc()))
                self.fileExists = False
                self.triedOpen = True
            
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
                self.fileInfo = gnomevfs.get_file_info(self.URI, gnomevfs.FILE_INFO_DEFAULT)
            else:
                logging.warn("Cannot get info on non-existant file %s" % self.URI)

    def file_exists(self):
        """
        Checks if this file exists or not.
        """
        if self.triedOpen:
            return self.fileExists
        else:
            return gnomevfs.exists(self.get_uri_string())
            
    def force_new_filename(self, filename):
        """
        In the xfer process calling this method will cause the file to be
        copied with the newFilename and not just to the new location but
        retaining the old filename
       
        Useful if for some conversions a temp file is created that you dont
        want to retain the name of
        """
        self.forceNewFilename = filename
            
    def get_mimetype(self):
        self._get_file_info()
        try:
            return self.fileInfo.mime_type
        except ValueError:
            #Why is gnomevfs so stupid and must I do this for
            #non local URIs??
            return gnomevfs.get_mime_type(self.URI)
        
    def get_uri_string(self):
        return self.URI
        
    def get_modification_time(self):
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
        return gnomevfs.read_entire_file(self.URI)
        
    def create_local_tempfile(self):
        """
        Creates a local temporary file copy of the vfs file. This is useful
        for non gnomevfs enabled libs

        @returns: local absolute path the the newly created temp file or
        None on error
        @rtype: C{string}
        """
        #Get a temporary file name
        tempname = tempfile.mkstemp()[1]
        toURI = gnomevfs.URI(tempname)
        fromURI = gnomevfs.URI(self.URI)
        #Xfer to the temp file. 
        gnomevfs.xfer_uri( fromURI, toURI,
                           gnomevfs.XFER_DEFAULT,
                           gnomevfs.XFER_ERROR_MODE_ABORT,
                           gnomevfs.XFER_OVERWRITE_MODE_REPLACE)
        return tempname

    def compare(self, A, B):
        """
        Compare A with B based upon their modification times
        """
        #If B doesnt exist then A is clearly newer
        if not gnomevfs.exists(B.get_uri_string()):
            return conduit.datatypes.COMPARISON_NEWER

        #Else look at the modification times
        aTime = A.get_modification_time()
        bTime = B.get_modification_time()
        #logging.debug("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (A.URI, aTime, B.URI, bTime))
        if aTime is None:
            return conduit.datatypes.COMPARISON_UNKNOWN
        if bTime is None:            
            return conduit.datatypes.COMPARISON_UNKNOWN
        
        #Is A less (older) than B?
        if aTime < bTime:
            return conduit.datatypes.COMPARISON_OLDER
        #Is A greater (newer) than B
        elif aTime > bTime:
            return conduit.datatypes.COMPARISON_NEWER
        elif aTime == bTime:
            aSize = A.get_size()
            bSize = B.get_size()
            #logging.debug("Comparing %s (SIZE: %s) with %s (SIZE: %s)" % (A.URI, aSize, B.URI, bSize))
            #If the times are equal, and the sizes are equal then assume
            #that they are the same.
            #FIXME: Shoud i check md5 instead?
            if aSize == None or bSize == None:
                #In case of error
                return conduit.datatypes.COMPARISON_UNKNOWN
            elif aSize == bSize:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                #shouldnt get here
                logging.error("Error comparing file sizes")
                return conduit.datatypes.COMPARISON_UNKNOWN
                
        else:
            logging.error("Error comparing file modification times")
            return conduit.datatypes.COMPARISON_UNKNOWN
            
def TaggedFile(File):
    """
    A simple class to allow tags to be applied to files for those
    dataproviders that need this information (e.g. f-spot)
    """
    def __init__(self):
        File.__init__(self)
        self.tags = []
    
    def set_tags(self, tags):
        self.tags = tags

    def get_tags(self, tags):
        return self.tags

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)
