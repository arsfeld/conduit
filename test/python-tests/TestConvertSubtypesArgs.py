#common sets up the conduit environment
from common import *
import conduit.Utils as Utils

tc = SimpleTest().type_converter

# file -> file
f, t, a = tc._get_conversion("file", "file")
ok("file -> file = file -> file", f == "file" and t == "file" and a == {})

f, t, a = tc._get_conversion("file?foo=bar", "file")
ok("file -> file = file -> file (ignore source args)", f == "file" and t == "file" and a == {})

f, t, a = tc._get_conversion("file", "file?foo=bar")
ok("file -> file = file -> file (respect dest args)", f == "file" and t == "file" and a == {"foo":"bar"})

# file -> file/audio
f, t, a = tc._get_conversion("file", "file/audio")
ok("file -> file/audio = file -> file/audio", f == "file" and t == "file/audio" and a == {})

f, t, a = tc._get_conversion("file?foo=bar", "file/audio")
ok("file -> file/audio = file -> file/audio (ignore source args)", f == "file" and t == "file/audio" and a == {})

f, t, a = tc._get_conversion("file", "file/audio?foo=bar")
ok("file -> file/audio = file -> file/audio (respect dest args)", f == "file" and t == "file/audio" and a == {"foo":"bar"})

# file/audio -> file
f, t, a = tc._get_conversion("file/audio", "file")
ok("file/audio -> file = file -> file", f == "file" and t == "file" and a == {})

f, t, a = tc._get_conversion("file/audio?foo=bar", "file")
ok("file/audio -> file = file -> file (ignore source args)", f == "file" and t == "file" and a == {})

f, t, a = tc._get_conversion("file/audio", "file?foo=bar")
ok("file/audio -> file = file -> file (respect dest args)", f == "file" and t == "file" and a == {"foo":"bar"})

# file/photo -> file/audio
f, t, a = tc._get_conversion("file/photo", "file/audio")
ok("file/photo -> file/audio = file/photo -> file/audio", f == "file/photo" and t == "file/audio" and a == {})

# transcode file/audio -> file/audio
f, t, a = tc._get_conversion("file/audio", "file/audio?foo=bar")
ok("file/audio -> file/audio = file/audio -> file/audio (respect dest args)", f == "file/audio" and t == "file/audio" and a == {"foo":"bar"})

# lots of args
args = {"foo":"bar","baz":"bob"}
f, t, a = tc._get_conversion("file", "file?%s" % Utils.encode_conversion_args(args))
ok("Multiple args: %s" % args, f == "file" and t == "file" and a == args)

finished()


