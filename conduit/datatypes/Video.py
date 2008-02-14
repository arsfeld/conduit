import conduit
import conduit.datatypes.File as File

#The preset encodings must be robust. That means, in the case of ffmpeg,
#you must be explicit with the options, otherwise it tries to retain sample
#rates between the input and output files, leading to invalid rates in the output
PRESET_ENCODINGS = {
    "divx":{"vcodec":"mpeg4","acodec":"ac3","arate":44100,"abitrate":"64k","format":"avi","vtag":"DIVX","file_extension":"avi", "fps":15},
    #breaks on single channel audio files because ffmpeg vorbis encoder only suuport stereo
    "ogg":{"vcodec":"theora","acodec":"vorbis","format":"ogg","file_extension":"ogg"},
    #needs mencoder or ffmpeg compiled with mp3 support
    "flv":{"arate":22050,"abitrate":32,"format":"flv","acodec":"mp3","mencoder":True,"file_extension":"flv"}   
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

class Video(File.File):

    _name_ = "file/video"

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)

    def get_video_duration(self):
        return None

    def get_video_size(self):
        return None,None


