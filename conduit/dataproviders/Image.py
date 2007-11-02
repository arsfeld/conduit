import conduit
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File
import conduit.dataproviders.DataProvider as DataProvider

class UploadInfo:
    """
    Upload information container, this way we can add info
    and keep the _upload_info method on the ImageSink retain
    its api
    """
    def __init__ (self, url, mimeType, name=None, tags=None):
        self.url = url
        self.mimeType = mimeType
        self.name = name
        self.tags = tags

class ImageSink(DataProvider.DataSink):
    """
    Abstract Base class for Image DataSinks
    """
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _module_type_ = "sink"
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"

    IMAGE_SIZES = ["640x480", "800x600", "1024x768"]
    NO_RESIZE = "None"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.need_configuration(True)
        
        self.username = ""

    def initialize(self):
        return True

    def _resize_combobox_build(self, combobox, selected):
        import gtk
        store = gtk.ListStore(str)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)  
        combobox.set_model(store)

        for s in [self.NO_RESIZE] + self.IMAGE_SIZES:
            rowref = store.append( (s,) )
            if s == selected:
                combobox.set_active_iter(rowref)

    def _resize_combobox_get_active(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return self.NO_RESIZE

        size = model[active][0]
        if size not in self.IMAGE_SIZES:
            return self.NO_RESIZE

        return size
        
    def _get_photo_info(self, photoID):
        """
        This should return the info for a given photo id,
        If this returns anything different from None, it will be
        passed onto _get_raw_photo_url 
        """
        return None

    def _get_raw_photo_url(self, photoInfo):
        """
        This should return the url of the online photo
        """
        return None

    def _upload_photo (self, uploadInfo):
        """
        Upload a photo
        """
        return None 

    def _replace_photo (self, id, uploadInfo):
        """
        Replace a photo with a new version
        """
        return id
        
    def _get_photo_formats (self):
        """
        This should return the allowed photo mimetypes
        """
        return ("image/jpeg", "image/png")
        
    def _get_default_format (self):
        """
        This should return the preferred format of images the sink accepts
        """
        return "image/jpeg"
        
    def _get_photo_size (self):
        """
        Return the preferred photo size string for rescaling, or None
        """
        return None        

    def put(self, photo, overwrite, LUID=None):
        """
        Accepts a vfs file. Must be made local.
        I also store a md5 of the photos uri to check for duplicates
        """
        DataProvider.DataSink.put(self, photo, overwrite, LUID)

        originalName = photo.get_filename()
        #Gets the local URI (/foo/bar). If this is a remote file then
        #it is first transferred to the local filesystem
        photoURI = photo.get_local_uri()
        mimeType = photo.get_mimetype()
        tags = photo.get_tags ()

        uploadInfo = UploadInfo(photoURI, mimeType, originalName, tags)
       
        #Check if we have already uploaded the photo
        if LUID != None:
            info = self._get_photo_info(LUID)
            #check if a photo exists at that UID
            if info != None:
                if overwrite == True:
                    #replace the photo
                    return self._replace_photo(LUID, uploadInfo)
                else:
                    #Only upload the photo if it is newer than the Remote one
                    url = self._get_raw_photo_url(info)
                    remoteFile = File.File(url)

                    #this is a limited test for equality type comparison
                    comp = photo.compare(remoteFile,True)
                    conduit.logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (photo.get_filename(),remoteFile.get_filename(),comp))
                    if comp != conduit.datatypes.COMPARISON_EQUAL:
                        raise Exceptions.SynchronizeConflictError(comp, photo, remoteFile)
                    else:
                        return LUID

        conduit.logd("Uploading Photo URI = %s, Mimetype = %s, Original Name = %s" % (photoURI, mimeType, originalName))

        #upload the file
        return self._upload_photo (uploadInfo)

    def delete(self, LUID):
        pass
 
    def is_configured (self):
        return False
        
    def get_input_conversion_args(self):
        args = {
                "formats" :             ','.join(self._get_photo_formats()),
                "default-format" :      self._get_default_format(),
                "size" :                self._get_photo_size(),
                }
        return args
        
    def set_configuration(self, config):
        DataProvider.DataSink.set_configuration(self, config)
        self.set_configured(self.is_configured())
    
class ImageTwoWay(DataProvider.DataSource, ImageSink):
    """
    Abstract Base Class for ImageTwoWay dataproviders
    """
    
    _module_type_ = "twoway"
    
    def __init__(self):
        DataProvider.DataSource.__init__(self)
        ImageSink.__init__(self)


