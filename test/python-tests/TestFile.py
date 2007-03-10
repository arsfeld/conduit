#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.Utils as Utils

try:
    f = File.File()
except:
    ok("Base: Must specify URI", True)
null = File.File("/foo/bar")
ok("Base: non-existant file", null.exists() == False)

remoteURIs = [  "ssh://root@www.greenbirdsystems.com/root/sync/Document.abw",
                "ssh://root@www.greenbirdsystems.com/root/sync/Image.png",
                "ssh://root@www.greenbirdsystems.com/root/sync/Tgz.tar.gz",
                "ssh://root@www.greenbirdsystems.com/root/sync/Text.txt",
                "ssh://root@www.greenbirdsystems.com/root/sync/Text",
                "ssh://root@www.greenbirdsystems.com/root/sync/tests/old/oldest",
                "ssh://root@www.greenbirdsystems.com/root/sync/tests/old/older",
                "ssh://root@www.greenbirdsystems.com/root/sync/tests/new/newer",
                "ssh://root@www.greenbirdsystems.com/root/sync/tests/new/newest"
                ]
localURIs = [   os.path.abspath(os.path.join(my_path,"tests","old","oldest")),
                os.path.abspath(os.path.join(my_path,"tests","old","older")),
                os.path.abspath(os.path.join(my_path,"tests","new","newer")),
                os.path.abspath(os.path.join(my_path,"tests","new","newest"))
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
    mtime = f.get_mtime()        
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
    mtime = f.get_mtime()        
    ok("Local: file mtime = %s" % mtime,mtime != None)
    size = f.get_size()
    ok("Local: file size = %s" % size,size != None)
    fname = f.get_filename()
    #Not a strict test because my get_filename() is a bit of a hack
    ok("Local: file name = %s" % fname,fname == Utils.get_filename(i))

comp = oldest.compare(older)
ok("Local Compare: checking oldest < older = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
comp = newest.compare(newer)
ok("Local Compare: checking newest > newer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
comp = newest.compare(newest)
ok("Local Compare: checking newest == newest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)
comp = oldest.compare(null)
ok("Local Compare: checking oldest w null = %s" % comp,comp == conduit.datatypes.COMPARISON_MISSING)

comp = roldest.compare(rolder)
ok("Remote Compare: checking roldest < rolder = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
comp = rnewest.compare(rnewer)
ok("Remote Compare: checking rnewest > rnewer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
comp = rnewest.compare(rnewest)
ok("Remote Compare: checking rnewest == rnewest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)
comp = roldest.compare(null)
ok("Remote Compare: checking roldest w null = %s" % comp,comp == conduit.datatypes.COMPARISON_MISSING)

comp = oldest.compare(rolder)
ok("Remote & Local Compare: checking oldest < rolder = %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)
comp = rnewest.compare(newer)
ok("Remote & Local Compare: checking rnewest > newer = %s" % comp,comp == conduit.datatypes.COMPARISON_NEWER)
comp = rnewest.compare(newest)
ok("Remote & Local Compare: checking rnewest == newest = %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)




