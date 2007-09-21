import conduit

from conduit.datatypes import File

class Music(File.File):

    _name_ = "file/music"

    def __init__(self, URI):
        File.File.__init__(self, URI=URI)


