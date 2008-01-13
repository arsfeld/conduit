import conduit
import conduit.datatypes.File as File

PRESET_ENCODINGS = {
    "ogg":{"acodec":"vorbis","format":"ogg","file_extension":"ogg"},
    "wav":{"acodec":"pcm_mulaw","format":"wav","file_extension":"wav"}
    }

class Audio(File.File):

    _name_ = "file/audio"

    def __init__(self, URI, **kwargs):
        File.File.__init__(self, URI, **kwargs)

    def get_audio_artist(self):
        return None

    def get_audio_album(self):
        return None

    def get_audio_duration(self):
        return None
