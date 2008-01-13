#common sets up the conduit environment
from common import *
import conduit.Vfs as Vfs
import conduit.Utils as Utils

ok("URI make canonical", Vfs.uri_make_canonical("file:///foo/bar/baz/../../bar//") == "file:///foo/bar")

safe = '/&=:@'
unsafe = ' !<>#%()[]{}'
safeunsafe = '%20%21%3C%3E%23%25%28%29%5B%5D%7B%7D'

ok("Dont escape path characters",Vfs.uri_escape(safe+unsafe) == safe+safeunsafe)
ok("Unescape back to original",Vfs.uri_unescape(safe+safeunsafe) == safe+unsafe)
ok("Get protocol", Vfs.uri_get_protocol("file:///foo/bar") == "file://")
ok("Get filename", Vfs.uri_get_filename("file:///foo/bar") == "bar")
ok("file:///home exists", Vfs.uri_exists("file:///home") == True)
ok("/home exists", Vfs.uri_exists("/home") == True)
ok("/foo/bar does not exist", Vfs.uri_exists("/foo/bar") == False)

tmpdiruri = Utils.new_tempdir()
newtmpdiruri = Vfs.uri_join(tmpdiruri, "foo", "bar", "baz")
Vfs.uri_make_directory_and_parents(newtmpdiruri)
ok("Made directory and parents: %s" % newtmpdiruri, Vfs.uri_exists(newtmpdiruri) == True)

# Test the folder scanner theading stuff
fileuri = Utils.new_tempfile("bla").get_local_uri()
stm = Vfs.FolderScannerThreadManager(maxConcurrentThreads=1)

def prog(*args): pass
def done(*args): pass

t1 = stm.make_thread("file:///tmp", False, prog, done)
t2 = stm.make_thread("file://"+tmpdiruri, False, prog, done)
stm.join_all_threads()

ok("Scanned /tmp ok - found %s" % fileuri, "file://"+fileuri in t1.get_uris())
ok("Scanned %s ok (empty)" % tmpdiruri, t2.get_uris() == [])

finished()
