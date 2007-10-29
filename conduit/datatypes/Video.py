import conduit
import conduit.datatypes.File as File

class Video(File.File):

    _name_ = "file/video"

    def __init__(self, URI):
        File.File.__init__(self, URI=URI)

    def get_duration(self):
        return None

    def get_size(self):
        return None,None


