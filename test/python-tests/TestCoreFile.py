#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.utils as Utils
import conduit.Vfs as Vfs

import os
import time
import datetime
import tempfile

if os.environ.has_key("CONDUIT_FILE_IMPL"):
    impls = (os.environ["CONDUIT_FILE_IMPL"],)
else:
    impls = ("GIO", "GnomeVfs")

for impl in impls:
    ok("--- TESTING FILE IMPL: %s" % impl, True)

    try:
        f = File.File(implName=impl)
    except:
        ok("Base: Must specify URI", True)

    null = File.File("/foo/bar",implName=impl)
    ok("Base: non-existant file", null.exists() == False)

    #test tempfile handling
    temp = Utils.new_tempfile(Utils.random_string(), implName=impl)
    ok("Base: Detected tempfile", temp.is_local() and temp._is_tempfile())

    uri = temp.get_local_uri()
    ok("Base: Tempfile in temp dir", uri and uri.startswith(tempfile.gettempdir()))

    temp.delete()
    gone = File.File(uri,implName=impl)
    ok("Base: Delete tempfile", not gone.exists())

    #test making directories
    tmpdir = Utils.new_tempdir()
    tmpdir2 = os.path.join(tmpdir, "subdir")
    f = File.File(tmpdir2,implName=impl)
    ok("Base: make directory", f.make_directory() == True)

    temp = Utils.new_tempfile(Utils.random_string(), implName=impl)
    temp.set_contents_as_text("123")
    contents = temp.get_contents_as_text()
    ok("Base: wrote contents", contents == "123")

    temp.set_contents_as_text("456")
    contents = temp.get_contents_as_text()
    ok("Base: wrote contents again", contents == "456")

    tempsize = random.randint(100, 200)
    contents = "a"*tempsize
    temp.set_contents_as_text(contents)
    ok( "Base: file size is accurate", temp.get_size() == tempsize )

    remUri = get_external_resources('folder')['removable-volume']
    rf = File.File(remUri,implName=impl)
    if Vfs.uri_exists(remUri):
        ok("Base: Removable volume detected", rf.is_on_removale_volume() == True)
        ok("Base: Removable volume calculate root path", rf.get_removable_volume_root_uri() == remUri)

    folder = File.File(os.environ["HOME"],implName=impl)
    ok("Base: check if HOME exists", folder.exists() == True)
    ok("Base: check if HOME is folder", folder.is_directory() == True)

    localURIs = [   os.path.abspath(os.path.join(my_path,"..", "test-data","oldest")),
                    os.path.abspath(os.path.join(my_path,"..", "test-data","older")),
                    os.path.abspath(os.path.join(my_path,"..", "test-data","newer")),
                    os.path.abspath(os.path.join(my_path,"..", "test-data","newest"))
                ]

    #test the comparison of files by mtime
    oldest = File.File(localURIs[0],implName=impl)
    older = File.File(localURIs[1],implName=impl)
    newer = File.File(localURIs[2],implName=impl)
    newest = File.File(localURIs[3],implName=impl)

    for i in localURIs:
        f = File.File(i,implName=impl)
        ok("Local: %s exists" % i, f.exists())
        remote = f.is_local() == 1
        # these might not be local, we might be on nfs after all!
        ok("Local: is local = %s" % remote,remote,die=False)
        mime = f.get_mimetype()
        ok("Local: file mimetype = %s" % mime,type(mime) == str and len(mime) > 0)
        mtime = f.get_mtime()        
        ok("Local: file mtime = %s" % mtime,mtime != None)
        size = f.get_size()
        #the files are 5 bytes in size
        ok("Local: file size = %s" % size,size == 5)
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
    f1 = Utils.new_tempfile(Utils.random_string(), implName=impl)
    f2 = os.path.join(tmpdir,"I am", "a", "path with spaces", "foo.txt")

    f3 = Utils.new_tempfile(Utils.random_string(), implName=impl)
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


        roldest = File.File(remoteURIs[5],implName=impl)
        rolder = File.File(remoteURIs[6],implName=impl)
        rnewer = File.File(remoteURIs[7],implName=impl)
        rnewest = File.File(remoteURIs[8],implName=impl)

        #test rebasing a remote file to local and returning its uri
        lrnewer = File.File(remoteURIs[1],implName=impl)
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
            f = File.File(i,implName=impl)
            ok("Remote: %s exists" % i, f.exists())
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
        
        tmpdir = tempfile.mkdtemp()
        ok("Created tempdir %s" % tmpdir, True)

        #remote file on readonly location
        f = File.File("http://files.conduit-project.org/screenshot.png",implName=impl)
        ok("Remote file exists", f.exists() == True)

        #make another local file
        local = Utils.new_tempfile(Utils.random_string(), implName=impl)

        #save the old information
        fOldName = f.get_filename()
        fOldSize = f.get_size()
        fOldMtime = f.get_mtime()
        localOldName = local.get_filename()
        localOldSize = local.get_size()
        localOldMtime = local.get_mtime()

        ok("Got R/O file info (%s)" % fOldName, fOldSize > 0 and fOldMtime != None)
        ok("Got file info (%s)" % localOldName, localOldSize > 0 and localOldMtime != None)

        #the new filenames
        fNewName = Utils.random_string()
        localNewName = Utils.random_string()
        newDate = datetime.datetime(1983,8,16)

        #change the filenames
        f.force_new_filename(fNewName)
        local.force_new_filename(localNewName)
        ok("Renamed R/O file correctly (%s)" % fNewName, fNewName == f.get_filename())
        ok("Renamed correctly (%s)" % localNewName, localNewName == local.get_filename())

        #change the file mtime
        f.force_new_mtime(newDate)
        local.force_new_mtime(newDate)
        ok("Set mtime R/O file mtime correctly (%s)" % fNewName, f.get_mtime() == newDate)
        ok("Set mtime correctly (%s)" % localNewName, local.get_mtime() == newDate)

        #transfer to new directory and check that the filenames get withheld in the transfer
        f.transfer(tmpdir)
        local.transfer(tmpdir)
        ok("Transferred R/O file correctly (%s)" % fNewName, f.get_filename() == fNewName)
        ok("Transferred correctly (%s)" % localNewName, local.get_filename() == localNewName)

        #play with proxy files, i.e. files that are like remote files, but stop being such
        #when transferred to the local system
        day0 = datetime.datetime(1983,8,16)
        day1 = datetime.datetime(1983,8,17)

        #compare two proxy files based on mtime only
        f = File.ProxyFile(
                    URI=get_external_resources("file")["remote"],
                    name=None,
                    modified=day0,
                    size=None,
                    implName=impl)
        f2 = File.ProxyFile(
                    URI=get_external_resources("file")["remote"],
                    name=None,
                    modified=day1,
                    size=None,
                    implName=impl)
        comp = f.compare(f2)
        ok("Proxy file comparison (mtime): %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)

        #compare two proxy files based on size only
        proxyFileName = Utils.random_string()
        f = File.ProxyFile(
                    URI=get_external_resources("file")["remote"],
                    name=None,
                    modified=day0,
                    size=10,
                    implName=impl)
        f2 = File.ProxyFile(
                    URI=get_external_resources("file")["remote"],
                    name=proxyFileName,
                    modified=day0,
                    size=10,
                    implName=impl)
        comp = f.compare(f2)
        ok("Proxy file comparison (size): %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)

        f2.transfer(tmpdir)
        ok("Transferred ProxyFile correctly (%s)" % proxyFileName, f2.get_filename() == proxyFileName)

        ok("ProxyFile graduated to real file", f2._is_proxyfile() == False)    

    #Now go back and test successful, i.e. non temp file, mtime and setting
    nn = "new name"
    nmt = datetime.datetime(2007,10,29)

    #remember old data
    f = File.File(localURIs[0],implName=impl)
    on = f.get_filename()
    omt = f.get_mtime()

    f.force_new_filename(nn)
    ok("Local: set new name", f.get_filename() == nn)

    f.force_new_mtime(nmt)
    ok("Local: set new mtime", f.get_mtime() == nmt)

    #restore old values
    f.force_new_filename(on)
    f.force_new_mtime(omt)



finished()


