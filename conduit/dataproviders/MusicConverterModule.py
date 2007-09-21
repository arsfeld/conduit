import conduit

import conduit.datatypes.File as File
import conduit.datatypes.Music as Music

MODULES = {
        "GstreamerConverter" :  { "type": "converter" }
}

#FIXME: These should be regexes applied on the mime_type
MUSIC_TYPES = (
    "audio/mpeg"
    )

class GstreamerConverter:
    def __init__(self):
        self.conversions =  {
                            "file/music,file/music"     :   self.transcode,    
                            "file,file/music"           :   self.file_to_music
                            }
                            
    def transcode(self, music, **kwargs):
        conduit.log("Transcode Music")
        return music

    def file_to_music(self, f, **kwargs):
        t = f.get_mime_type()
        if t in MUSIC_TYPES:
            return Music.Music(URI=f._get_text_uri())
        else:
            return None

