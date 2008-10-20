import conduit
import conduit.datatypes.File as File
import conduit.utils.MediaFile as MediaFile

PRESET_ENCODINGS = {
    "divx":{"vcodec":"xvidenc", "acodec":"lame", "format":"avimux", "vtag":"DIVX", "file_extension":"avi", "mimetype": "video/x-msvideo"},
    #FIXME: The following comment has not been tested with GStreamer, it may or may not still be true:
    # breaks on single channel audio files because ffmpeg vorbis encoder only suuport stereo
    "ogg":{"vcodec":"theoraenc", "acodec":"vorbisenc", "format":"oggmux", "file_extension":"ogg"},
    #requires gst-ffmpeg and gst-plugins-ugly
    "flv":{"vcodec":"ffenc_flv", "acodec":"lame", "format":"ffmux_flv", "file_extension":"flv"}
    }

def mimetype_is_video(mimetype):
    """
    @returns: True if the given mimetype string represents a video file
    """
    if mimetype.startswith("video/"):
        return True
    elif mimetype == "application/ogg":
        return True
    else:
        return False

class Video(MediaFile.MediaFile):

    _name_ = "file/video"

    def __init__(self, URI, **kwargs):
        MediaFile.MediaFile.__init__(self, URI, **kwargs)

    def get_video_duration(self):
        '''
        Video duration, in milisecs (int)
        '''
        return self._get_metadata('duration')

    def get_video_size(self):
        '''
        Video size, as a tuple (width, height), both in pixels (int, int)
        '''
        return self._get_metadata('width'), self._get_metadata('height')
