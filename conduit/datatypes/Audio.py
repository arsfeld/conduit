import conduit
import conduit.datatypes.File as File

PRESET_ENCODINGS = {
    "ogg":{"acodec":"vorbis","format":"ogg"},
    "wav":{"acodec":"pcm_mulaw","format":"wav"}
    }

class Audio(File.File):

    _name_ = "file/audio"

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)

    def get_artist(self):
        return None

    def get_album(self):
        return None

    def get_duration(self):
        return None
