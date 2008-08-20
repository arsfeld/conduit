import conduit
import conduit.datatypes.File as File
import logging
log = logging.getLogger("datatypes.Audio")

import pygst
pygst.require('0.10')
import gst
from gst.extend import discoverer
import threading
from threading import Lock

class MediaFile(File.File):

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)

    def _create_gst_metadata(self):
        '''
        Get metadata from GStreamer
        '''
        event = threading.Event()
        def discovered(discoverer, valid):
            if not valid:
                log.debug("Media file not valid")
                #FIXME: What exception should be raised here?
                raise Exception
            event.set()
        # FIXME: Using Discoverer for now, but we should switch to utils.GstMetadata
        #        when we get thumbnails working on it.
        info = discoverer.Discoverer(self.get_local_uri())
        info.connect('discovered', discovered)
        info.discover()
        # Wait for discover to finish (which is async and emits discovered)
        event.wait()
        tags = info.tags
        if info.is_video:
            tags['width'] = info.videowidth
            tags['height'] = info.videoheight
            tags['videorate'] = info.videorate
            tags['duration'] = info.videolength / gst.MSECOND
        if info.is_audio:
            tags['duration'] = info.audiolength / gst.MSECOND
            tags['samplerate'] = info.audiorate
            tags['channels'] = info.audiochannels
        return tags

    def _get_metadata(self, name):
        tags = self.get_media_tags()
        if name in tags:
            return tags[name]
        else:
            return None

    def __getattr__(self, name):
        # Get metadata only when needed
        if name == 'gst_tags':
            tags = self.gst_tags = self._create_gst_metadata()
            return tags
        else:
            raise AttributeError

    def get_media_tags(self):
        '''
        Get a dict containing all availiable metadata.

        Descendants should override this function to provide their own tags,
        or merge with these tags.
        '''
        return self.gst_tags
