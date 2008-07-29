#common sets up the conduit environment
from common import *
import conduit.Vfs as Vfs
import conduit.utils as Utils

ok("URI make canonical", Vfs.uri_make_canonical("file:///foo/bar/baz/../../bar//") == "file:///foo/bar")

safe = '/&=:@'
unsafe = ' !<>#%()[]{}'
safeunsafe = '%20%21%3C%3E%23%25%28%29%5B%5D%7B%7D'

ok("Dont escape path characters",Vfs.uri_escape(safe+unsafe) == safe+safeunsafe)
ok("Unescape back to original",Vfs.uri_unescape(safe+safeunsafe) == safe+unsafe)
ok("Get protocol", Vfs.uri_get_protocol("file:///foo/bar") == "file://")
name, ext = Vfs.uri_get_filename_and_extension("file:///foo/bar.ext")
ok("Get filename (%s,%s)" % (name,ext), name == "bar" and ext == ".ext")
ok("file:///home exists", Vfs.uri_exists("file:///home") == True)
ok("/home exists", Vfs.uri_exists("/home") == True)
ok("/home is folder", Vfs.uri_is_folder("/home") == True)
ok("/foo/bar does not exist", Vfs.uri_exists("/foo/bar") == False)
ok("format uri", Vfs.uri_format_for_display("file:///foo") == "/foo")

tmpdiruri = Utils.new_tempdir()
newtmpdiruri = Vfs.uri_join(tmpdiruri, "foo", "bar", "baz")
Vfs.uri_make_directory_and_parents(newtmpdiruri)
ok("Made directory and parents: %s" % newtmpdiruri, Vfs.uri_exists(newtmpdiruri) == True)

# Test the folder scanner theading stuff
fileuri = Utils.new_tempfile("bla").get_local_uri()
stm = Vfs.FolderScannerThreadManager(maxConcurrentThreads=1)

def prog(*args): pass
def done(*args): pass

t1 = stm.make_thread("file:///tmp", False, False, prog, done)
t2 = stm.make_thread("file://"+tmpdiruri, False, False, prog, done)
stm.join_all_threads()

ok("Scanned /tmp ok - found %s" % fileuri, "file://"+fileuri in t1.get_uris())
ok("Scanned %s ok (empty)" % tmpdiruri, t2.get_uris() == [])

# Test the volume management stuff
ntfsUri = get_external_resources('folder')['ntfs-volume']
fstype = Vfs.uri_get_filesystem_type(ntfsUri)
ok("Get filesystem type (%s)" % fstype,fstype == "ntfs")
ok("Escape illegal chars in filenames", 
        Vfs.uri_sanitize_for_filesystem("invalid:name","ntfs") == "invalid name")
ok("Escape illegal chars in uris", 
        Vfs.uri_sanitize_for_filesystem("file:///i:n/i:n","ntfs") == "file:///i n/i n")

localUri = get_external_resources('folder')['folder']
ok("Local uri --> path", Vfs.uri_to_local_path(localUri) == "/tmp")
ok("Local uri not removable", Vfs.uri_is_on_removable_volume(localUri) == False)

removableUri = get_external_resources('folder')['removable-volume']
ok("Removable volume detected removable", Vfs.uri_is_on_removable_volume(removableUri))
ok("Removable volume calculate root path", Vfs.uri_get_volume_root_uri(removableUri).startswith("file:///media/"))

URIS_TO_JOIN = (
    (   ("file:///foo/bar","gax","ssss"),   
        "file:///foo/bar/gax/ssss"),
    (   ("smb://192.168.1.1","Disk-2","Travel%20Videos/","Switzerland"),
        "smb://192.168.1.1/Disk-2/Travel%20Videos/Switzerland"),
    (   ("ssh://john@open.grcnz.com/home","john","phd"),
        "ssh://john@open.grcnz.com/home/john/phd"),
    (   ("foo","bar","baz"),
        "foo/bar/baz")
)

for parts, result in URIS_TO_JOIN:
    ok("Join uri: %s" % result, Vfs.uri_join(*parts) == result)
    
RELATIVE_URIS = (
    #from                   #to                         #relativ    
(   "file:///foo/bar",      "file:///baz/bob",          "file:///baz/bob"   ),
(   "file:///foo/bar",      "file:///foo/bar/baz/bob",  "baz/bob"           ),
(   "file:///foo/bar",      "file:///foo/bar/baz",      "baz"               ))
for f,t,result in RELATIVE_URIS:
    ok("Get relative uri: %s" % result, Vfs.uri_get_relative(f,t) == result)
    
VALID_URIS = (
    #uri                                #valid
(   "smb://192.168.1.1/foo/bar",        True                        ),
(   "ftp://192.168.1.1/foo/bar",        True                        ),
(   "file:///foo/bar",                  True                        ),
(   "file:/foo/bar",                    False                       ),
(   "ftp:192.168.1.1",                  False                       ),
(   "/foo/bar",                         False                       ))
for uri,result in VALID_URIS:
    desc = ("Invalid","Valid")[int(result)]
    ok("%s uri: %s" % (desc,uri),Vfs.uri_is_valid(uri) == result)

finished()
