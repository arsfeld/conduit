#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.Utils as Utils

if __name__ == '__main__':
    try:
        f = File.File()
    except:
        ok("Base: empty constructor", True)
    null = File.File("/foo/bar")
    ok("Base: non-existant file", null.exists() == False)

    remoteURIs = [  "ssh://root@www.greenbirdsystems.com/root/sync/Document.abw",
                    "ssh://root@www.greenbirdsystems.com/root/sync/Image.png",
                    "ssh://root@www.greenbirdsystems.com/root/sync/Tgz.tar.gz",
                    "ssh://root@www.greenbirdsystems.com/root/sync/Text.txt",
                    "ssh://root@www.greenbirdsystems.com/root/sync/Text",
                    "ssh://root@www.greenbirdsystems.com/root/sync/tests/old/file1",
                    "ssh://root@www.greenbirdsystems.com/root/sync/tests/old/file2",
                    "ssh://root@www.greenbirdsystems.com/root/sync/tests/new/file1",
                    "ssh://root@www.greenbirdsystems.com/root/sync/tests/new/file2"
                    ]
    localURIs = [   os.path.abspath(os.path.join(my_path,"tests","old","file1")),
                    os.path.abspath(os.path.join(my_path,"tests","old","file2")),
                    os.path.abspath(os.path.join(my_path,"tests","new","file1")),
                    os.path.abspath(os.path.join(my_path,"tests","new","file2"))
                ]

    #listed from oldest to newest in two blocks
    comparisonURIs = localURIs + remoteURIs[5:]

    #test the comparison of files by mtime
    oldest = File.File(comparisonURIs[0])
    older = File.File(comparisonURIs[1])
    newer = File.File(comparisonURIs[2])
    newest = File.File(comparisonURIs[3])
    roldest = File.File(comparisonURIs[4])
    rolder = File.File(comparisonURIs[5])
    rnewer = File.File(comparisonURIs[6])
    rnewest = File.File(comparisonURIs[7])
    #test rebasing a remote file to local and returning its uri
    lrnewer = File.File(comparisonURIs[6])
    lrneweruri = lrnewer.get_local_uri()
    ok("Base: getting local copy of a remote file = %s" % lrneweruri,type(lrneweruri) == str and len(lrneweruri) > 0)


    for i in remoteURIs:
        f = File.File(i)
        remote = f.is_local() == 0
        ok("Remote: is remote = %s" % remote,remote)
        mime = f.get_mimetype()
        ok("Remote: file mimetype = %s" % mime,type(mime) == str and len(mime) > 0)
        mtime = f.get_modification_time()        
        ok("Remote: file mtime = %s" % mtime,mtime != None)
        size = f.get_size()
        ok("Remote: file size = %s" % size,size != None)
        fname = f.get_filename()
        #Not a strict test because my get_filename() is a bit of a hack
        ok("Remote: file name = %s" % fname,fname == Utils.get_filename(i))

    for i in localURIs + [lrnewer]:
        if type(i) == str:
            f = File.File(i)
        #eew special case for lrnewer
        else:
            f = i
            i = lrneweruri
        remote = f.is_local() == 1
        ok("Local: is local = %s" % remote,remote)
        mime = f.get_mimetype()
        ok("Local: file mimetype = %s" % mime,type(mime) == str and len(mime) > 0)
        mtime = f.get_modification_time()        
        ok("Local: file mtime = %s" % mtime,mtime != None)
        size = f.get_size()
        ok("Local: file size = %s" % size,size != None)
        fname = f.get_filename()
        #Not a strict test because my get_filename() is a bit of a hack
        ok("Local: file name = %s" % fname,fname == Utils.get_filename(i))

    comp = oldest.compare(oldest, older)
    ok("Local Compare: checking oldest < older = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
    comp = oldest.compare(newest, newer)
    ok("Local Compare: checking newest > newer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
    comp = oldest.compare(newest, newest)
    ok("Local Compare: checking newest == newest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)
    comp = oldest.compare(oldest, null)
    ok("Local Compare: checking oldest > null = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)

    comp = oldest.compare(roldest, rolder)
    ok("Remote Compare: checking roldest < rolder = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
    comp = oldest.compare(rnewest, rnewer)
    ok("Remote Compare: checking rnewest > rnewer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
    comp = oldest.compare(rnewest, rnewest)
    ok("Remote Compare: checking rnewest == rnewest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)
    comp = oldest.compare(roldest, null)
    ok("Local Compare: checking roldest > null = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)

    comp = oldest.compare(oldest, rolder)
    ok("Remote & Local Compare: checking oldest < rolder = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
    comp = oldest.compare(rnewest, newer)
    ok("Remote & Local Compare: checking rnewest > newer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
    comp = oldest.compare(rnewest, newest)
    ok("Remote & Local Compare: checking rnewest == newest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)




