from common import *

import traceback

import conduit.datatypes.File as File
import conduit.datatypes.Video as Video
import conduit.datatypes.Audio as Audio
import conduit.Utils as Utils
import conduit.modules.AudioVideoConverterModule as AVModule

FILES = (
#uri                                                                        #conversion args
("/home/john/Videos/photoriver.mov",                                        Video.PRESET_ENCODINGS['flv']),
("/home/john/Videos/photoriver.mov",                                        Video.PRESET_ENCODINGS['divx']),
("/home/john/Videos/photoriver.mov",                                        Video.PRESET_ENCODINGS['ogg']),
("/home/john/Music/01 - Problems.mp3",                                      Audio.PRESET_ENCODINGS['ogg'])
)

test = SimpleTest()
tc = test.type_converter

ok("Video Conversion exists", tc.conversion_exists("file","file/video") == True)
ok("Audio Conversion exists", tc.conversion_exists("file","file/audio") == True)

for uri, args in FILES:
    f = File.File(uri)
    if f.exists():
        mimeType = f.get_mimetype()
        if mimeType.startswith("video/") or mimeType.startswith("audio/"):
            to_type = "file/%s?%s" % (mimeType.split("/")[0],Utils.encode_conversion_args(args))
            try:
                newdata = tc.convert("file",to_type, f)
                ok("Conversion -> %s%s" % f.get_filename_and_extension(), newdata != None and newdata.exists())
            except Exception:
                traceback.print_exc()
                ok("Conversion failed", False)

finished()


