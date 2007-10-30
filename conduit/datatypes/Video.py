import conduit
import conduit.datatypes.File as File

PRESET_ENCODINGS = {
    "divx":{"vcodec":"mpeg4","acodec":"ac3","format":"avi","vtag":"DIVX"},
    "ogg":{"vcodec":"theora","acodec":"vorbis","format":"ogg"},
    #needs mencoder or ffmpeg compiled with mp3 support
    "flv":{'arate':22050,'abitrate':32,'format':'flv','acodec':'mp3','mencoder':True}   
    }

class Video(File.File):

    _name_ = "file/video"

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)

    def get_duration(self):
        return None

    def get_size(self):
        return None,None


