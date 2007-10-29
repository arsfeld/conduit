import conduit
import conduit.datatypes.File as File

class Audio(File.File):

    _name_ = "file/audio"

    def __init__(self, URI):
        File.File.__init__(self, URI=URI)

    def get_artist(self):
        return None

    def get_album(self):
        return None

    def get_duration(self):
        return None
