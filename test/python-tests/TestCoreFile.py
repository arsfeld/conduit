#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.utils as Utils
import conduit.Vfs as Vfs

import os

try:
    f = File.File()
except:
    ok("Base: Must specify URI", True)

null = File.File("/foo/bar")
ok("Base: non-existant file", null.exists() == False)

try:
    f.get_filename()
    ok("Base: Cannot get info on non-existant file", False)
except:
    ok("Base: Cannot get info on non-existant file", True)

folder = File.File(os.environ["HOME"])
ok("Base: check if HOME exists", folder.exists() == True)
ok("Base: check if HOME is folder", folder.is_directory() == True)

localURIs = [   os.path.abspath(os.path.join(my_path,"..", "test-data","oldest")),
                os.path.abspath(os.path.join(my_path,"..", "test-data","older")),
                os.path.abspath(os.path.join(my_path,"..", "test-data","newer")),
                os.path.abspath(os.path.join(my_path,"..", "test-data","newest"))
            ]

#test the comparison of files by mtime
oldest = File.File(localURIs[0])
older = File.File(localURIs[1])
newer = File.File(localURIs[2])
newest = File.File(localURIs[3])

for i in localURIs:
    f = File.File(i)
    remote = f.is_local() == 1
    ok("Local: is local = %s" % remote,remote)
    mime = f.get_mimetype()
    ok("Local: file mimetype = %s" % mime,type(mime) == str and len(mime) > 0)
    mtime = f.get_mtime()        
    ok("Local: file mtime = %s" % mtime,mtime != None)
    size = f.get_size()
    ok("Local: file size = %s" % size,size != None)
    fname = f.get_filename()
    #Not a strict test because my get_filename() is a bit of a hack
    ok("Local: file name = %s" % fname,fname == Vfs.uri_get_filename(i))

comp = oldest.compare(older)
ok("Local Compare: checking oldest < older = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
comp = newest.compare(newer)
ok("Local Compare: checking newest > newer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
comp = newest.compare(newest)
ok("Local Compare: checking newest == newest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)
comp = oldest.compare(null)
ok("Local Compare: checking oldest w null = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)

#test the handling of weird characters and transferring files to unusual paths
tmpdir = Utils.new_tempdir()
f1 = Utils.new_tempfile(Utils.random_string())
f2 = os.path.join(tmpdir,"I am", "a", "path with spaces", "foo.txt")

f3 = Utils.new_tempfile(Utils.random_string())
f4 = os.path.join(tmpdir,"I also am", "a", "wierd path", "foo.txt")

f1.transfer(f2)
f3.transfer(f4)

if is_online():
    #so conduit asks me for my password
    remoteURIs = [  "http://www.gnome.org/~jstowers/conduit_test_data/Document.abw",
                    "http://www.gnome.org/~jstowers/conduit_test_data/Image.png",
                    "http://www.gnome.org/~jstowers/conduit_test_data/Tgz.tar.gz",
                    "http://www.gnome.org/~jstowers/conduit_test_data/Text.txt",
                    "http://www.gnome.org/~jstowers/conduit_test_data/Text",
                    "http://www.gnome.org/~jstowers/conduit_test_data/oldest",
                    "http://www.gnome.org/~jstowers/conduit_test_data/older",
                    "http://www.gnome.org/~jstowers/conduit_test_data/newer",
                    "http://www.gnome.org/~jstowers/conduit_test_data/newest"
                    ]


    roldest = File.File(remoteURIs[5])
    rolder = File.File(remoteURIs[6])
    rnewer = File.File(remoteURIs[7])
    rnewest = File.File(remoteURIs[8])

    #test rebasing a remote file to local and returning its uri
    lrnewer = File.File(remoteURIs[1])
    lrnewerfname = Vfs.uri_get_filename(remoteURIs[1])
    lrneweruri = lrnewer.get_local_uri()
    ok("Base: getting local copy of a remote file = %s" % lrneweruri,type(lrneweruri) == str and len(lrneweruri) > 0)
    remote = lrnewer.is_local() == 1
    ok("Local: is local = %s" % remote,remote)
    mime = lrnewer.get_mimetype()
    ok("Local: file mimetype = %s" % mime,type(mime) == str and len(mime) > 0)
    mtime = lrnewer.get_mtime()        
    ok("Local: file mtime = %s" % mtime,mtime != None)
    size = lrnewer.get_size()
    ok("Local: file size = %s" % size,size != None)
    fname = lrnewer.get_filename()
    #Not a strict test because my get_filename() is a bit of a hack
    ok("Local: file name = %s" % fname,fname == lrnewerfname)

    for i in remoteURIs:
        f = File.File(i)
        remote = f.is_local() == 0
        ok("Remote: is remote = %s" % remote,remote)
        mime = f.get_mimetype()
        ok("Remote: file mimetype = %s" % mime,type(mime) == str and len(mime) > 0)
        mtime = f.get_mtime()        
        ok("Remote: file mtime = %s" % mtime,mtime != None)
        size = f.get_size()
        ok("Remote: file size = %s" % size,size != None)
        fname = f.get_filename()
        #Not a strict test because my get_filename() is a bit of a hack
        ok("Remote: file name = %s" % fname,fname == Vfs.uri_get_filename(i))


    comp = roldest.compare(rolder)
    ok("Remote Compare: checking roldest < rolder = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
    comp = rnewest.compare(rnewer)
    ok("Remote Compare: checking rnewest > rnewer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
    comp = rnewest.compare(rnewest)
    ok("Remote Compare: checking rnewest == rnewest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)
    comp = roldest.compare(null)
    ok("Remote Compare: checking roldest w null = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)

    comp = oldest.compare(rolder)
    ok("Remote & Local Compare: checking oldest < rolder = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER, False)
    comp = rnewest.compare(newer)
    ok("Remote & Local Compare: checking rnewest > newer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER, False)
    comp = rnewest.compare(newest)
    ok("Remote & Local Compare: checking rnewest == newest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL, False)

finished()


