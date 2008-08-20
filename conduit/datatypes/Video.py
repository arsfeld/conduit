import conduit
import conduit.datatypes.File as File
import conduit.utils.MediaFile as MediaFile

#The preset encodings must be robust. That means, in the case of ffmpeg,
#you must be explicit with the options, otherwise it tries to retain sample
#rates between the input and output files, leading to invalid rates in the output
# "arate":44100, "abitrate":"64k"
# "fps":15
PRESET_ENCODINGS = {
    "divx":{"vcodec":"xvidenc", "acodec":"lame", "format":"avimux", "vtag":"DIVX", "file_extension":"avi", },
    #breaks on single channel audio files because ffmpeg vorbis encoder only suuport stereo
    "ogg":{"vcodec":"theoraenc", "acodec":"vorbisenc", "format":"oggmux", "file_extension":"ogg"},
    #needs mencoder or ffmpeg compiled with mp3 support
    #requires gst-ffmpeg and gst-plugins-ugly
    "flv":{"vcodec":"ffenc_flv", "acodec":"lame", "format":"ffmux_flv", "file_extension":"flv"}
    #"arate":22050,"abitrate":32,
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
        return _get_metadata('duration')

    def get_video_size(self):
        return _get_metadata('width'),_get_metadata('height')
