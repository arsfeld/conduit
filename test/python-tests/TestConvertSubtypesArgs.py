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

# file -> file/music
f, t, a = tc._get_conversion("file", "file/music")
ok("file -> file/music = file -> file/music", f == "file" and t == "file/music" and a == {})

f, t, a = tc._get_conversion("file?foo=bar", "file/music")
ok("file -> file/music = file -> file/music (ignore source args)", f == "file" and t == "file/music" and a == {})

f, t, a = tc._get_conversion("file", "file/music?foo=bar")
ok("file -> file/music = file -> file/music (respect dest args)", f == "file" and t == "file/music" and a == {"foo":"bar"})

# file/music -> file
f, t, a = tc._get_conversion("file/music", "file")
ok("file/music -> file = file -> file", f == "file" and t == "file" and a == {})

f, t, a = tc._get_conversion("file/music?foo=bar", "file")
ok("file/music -> file = file -> file (ignore source args)", f == "file" and t == "file" and a == {})

f, t, a = tc._get_conversion("file/music", "file?foo=bar")
ok("file/music -> file = file -> file (respect dest args)", f == "file" and t == "file" and a == {"foo":"bar"})

# file/photo -> file/music
f, t, a = tc._get_conversion("file/photo", "file/music")
ok("file/photo -> file/music = file/photo -> file/music", f == "file/photo" and t == "file/music" and a == {})

# transcode file/music -> file/music
f, t, a = tc._get_conversion("file/music", "file/music?foo=bar")
ok("file/music -> file/music = file/music -> file/music (respect dest args)", f == "file/music" and t == "file/music" and a == {"foo":"bar"})

# lots of args
args = {"foo":"bar","baz":"bob"}
f, t, a = tc._get_conversion("file", "file?%s" % Utils.encode_conversion_args(args))
ok("Multiple args: %s" % args, f == "file" and t == "file" and a == args)

finished()


