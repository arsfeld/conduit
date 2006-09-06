import gnomevfs
import conduit
from conduit.datatypes import DataType

import os
import tempfile
import datetime

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
    vfsFile = File()
    vfsFile.load_from_uri(name)
    return vfsFile
    
class File(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self,"file")

        self.uriString = None                    
        self.vfsHandle = None
        self.fileInfo = None
        self.forceNewFilename = ""
        
    def _get_file_info(self):
        if self.fileInfo is None:
            self.fileInfo = gnomevfs.get_file_info(self.uriString, gnomevfs.FILE_INFO_DEFAULT)
            
    def force_new_filename(self, filename):
        """
        In the xfer process calling this method will cause the file to be
        copied with the newFilename and not just to the new location but
        retaining the old filename
       
        Useful if for some conversions a temp file is created that you dont
        want to retain the name of
        """
        self.forceNewFilename = filename
            
    def load_from_uri(self, uri):
        """
        Creates a vfsFile from a uri string
        """
        self.uriString = uri
        self.vfsFile = gnomevfs.Handle(self.uriString)
        
    def get_mimetype(self):
        self._get_file_info()
        try:
            return self.fileInfo.mime_type
        except ValueError:
            #Why is gnomevfs so stupid and must I do this for
            #non local URIs??
            return gnomevfs.get_mime_type(self.uriString)
        
    def get_uri_string(self):
        return self.uriString
        
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
                       
    def get_filename(self):
        """
        Returns the filename of the file
        """
        self._get_file_info()
        return self.fileInfo.name
        
    def get_contents_as_text(self):
        return gnomevfs.read_entire_file(self.uriString)
        
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
        fromURI = gnomevfs.URI(self.uriString)
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
            return conduit.datatypes.COMPARISON_EQUAL
        else:
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
