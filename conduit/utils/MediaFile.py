import threading
import conduit
import conduit.datatypes.File as File
import logging
log = logging.getLogger("datatypes.Audio")

try:
    import gst
    from gst.extend import discoverer
    GST_AVAILABLE = True
except ImportError:
    GST_AVAILABLE = False

class MediaFile(File.File):
    '''
    A MediaFile is a file with multimedia attributes, such as an audio or video
    file.
    
    This class includes methods to access metadata included in the file. 
    Using the GStreaner framework, it is able to retrieve most commonly used
    properties of this kind of file.
    
    Media providers can include their own data by overriding get_media_tags,
    and either providing a new set of properties, or call this class's
    get_media_tags to merge their data with the GStreamer properties.
    
    The Audio and Video classes expose these properties as convenient
    methods. Note that a descendant of this class only needs to put their
    data in get_media_tags for them to be exposed by the Audio and Video 
    classes. However, they need to follow the types and units of the GStreamer
    properties, which are described in each of their methods.
    
    Retrieving metadata through GStreamer is a costly process, because the file
    must be accessed and processed. Thus, it is only retrieved when needed, when
    the gst_tags attribute is accessed. So, accessing any metadata starts a 
    chain reaction, which starts with descendants overriding get_media_tags,
    eventually calling get_media_tags in this class, then accesses gst_tags,
    thus creating the gst metadata if needed.
    '''

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)

    def _create_gst_metadata(self):
        '''
        Create metadata from GStreamer
        '''
        event = threading.Event()
        def discovered(discoverer, valid):
            self._valid = valid
            event.set()
        # FIXME: Using Discoverer for now, but we should switch to utils.GstMetadata
        #        when we get it to work (and eventually support thumbnails).
        info = discoverer.Discoverer(self.get_local_uri())
        info.connect('discovered', discovered)
        info.discover()
        # Wait for discover to finish (which is async and emits discovered)
        event.wait()
        if self._valid:
            tags = info.tags
        else:
            log.debug("Media file not valid")
            return {}

        tags['mimetype'] = info.mimetype
        if info.is_video:
            tags['width'] = info.videowidth
            tags['height'] = info.videoheight
            tags['videorate'] = info.videorate
            tags['duration'] = info.videolength / gst.MSECOND
        if info.is_audio:
            tags['duration'] = info.audiolength / gst.MSECOND
            tags['samplerate'] = info.audiorate
            tags['channels'] = info.audiochannels
            tags['audiowidth'] = info.audiowidth
            tags['audiodepth'] = info.audiodepth
        return tags

    def _get_metadata(self, name):        
        tags = self.get_media_tags()
        if name in tags:
            return tags[name]
        return None

    def __getattr__(self, name):
        # Get metadata only when needed
        if name == 'gst_tags':
            tags = self.gst_tags = self._create_gst_metadata()
            # Don't call self.gst_tags here
            return tags
        else:
            raise AttributeError

    def get_media_tags(self):
        '''
        Get a dict containing all availiable metadata.

        Descendants should override this function to provide their own tags,
        or merge with these tags, by calling MediaFile.get_media_tags().
        '''
        if GST_AVAILABLE:
            return self.gst_tags
        return {}
    
    def get_media_mimetype(self):
        '''
        Return the file miemtype, as returned by GStreamer, which might differ
        from the file mimetype
        '''
        return self._get_metadata('mimetype')
