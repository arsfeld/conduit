from common import *
import conduit.datatypes.File as File
import conduit.utils as Utils

import os
import tempfile
import datetime
import random
import stat

tmpdir = tempfile.mkdtemp()
ok("Created tempdir %s" % tmpdir, True)

contents = Utils.random_string()
name = Utils.random_string()+".foo"
tmpFile = File.TempFile(contents)

tmpFile.force_new_filename(name)
ok("Set filename to %s" % name, tmpFile._newFilename == name)

newPath = os.path.join(tmpdir, name)
tmpFile.transfer(tmpdir)
ok("Transferred -> %s" % newPath, os.path.isfile(newPath))

f = File.File(newPath)
ok("File contents = %s" % contents, f.get_contents_as_text() == contents)
mtime = f.get_mtime()

f = File.File(newPath)
ok("File name ok", f.get_filename() == name)

#make some 'real' files to play with
testDir = os.path.join(os.environ['TEST_DIRECTORY'],"TempFile")
if not os.path.exists(testDir):
    os.mkdir(testDir)

testFiles = [
    ('/usr/bin/env','env',True,True),
    ('http://files.conduit-project.org/screenshot.png','screenshot.png',True,False)
    ]
for i in range(0,5):
    j = Utils.random_string()
    testFiles.append( (os.path.join(testDir,j),j,False,True) )

for path,i,readOnly,local in testFiles:
    #1) create files
    if not readOnly:
        j = open(path,'w')
        j.write(i)
        j.close()
    
    group = Utils.random_string()
    f = File.File(path,group=group)
    f.set_UID(Utils.random_string())
    uid = f.get_UID()
    size = f.get_size()
    mt = f.get_mimetype()
    
    #normal file operations on files, both r/o and writable
    ok("not tempfile (%s)" % i, not f._is_tempfile())
    ok("not tempfile uid ok", f.get_UID() == uid)
    ok("not tempfile filename ok", f.get_filename() == i)
    ok("not tempfile group ok", f.group == group)
    nn = i+"-renamed"
    f.force_new_filename(nn)
    ok("not tempfile renamed ok", f.get_filename() == nn)
    f.set_mtime(mtime)
    ok("not tempfile set_mtime ok", f.get_mtime() == mtime)

    #repeat the ops once we make the file a tempfile    
    if local:
        tmppath = f.to_tempfile()
    else:
        tmppath = f.get_local_uri()
    ok("tempfile (%s)" % tmppath, f.exists() and f._is_tempfile() and not f.is_directory())
    ok("tempfile uid ok", f.get_UID() == uid)
    ok("tempfile filename ok", f.get_filename() == nn)
    ok("tempfile group ok", f.group == group)
    ok("tempfile path is local", f.get_local_uri() == tmppath)

    #check the transfer was ok    
    size2 = f.get_size()
    ok("tempfile size is same", size == size2)
    mt2 = f.get_mimetype()
    ok("tempfile mimetype is same", mt == mt2)

    #check that subsequent renames/mtimes are always deferred
    #when the file is a tempfile
    nn = i+"-renamed-again"
    f.force_new_filename(nn)
    ok("tempfile filename ok again", f.get_filename() == nn)
    mtime2 = datetime.datetime.now()
    f.set_mtime(mtime2)
    ok("tempfile set_mtime ok again", f.get_mtime() == mtime2)
    
    #check we can create a second tempfile with the same props
    #and delete it, leaving the first tempfile behind
    tmppath2 = f.to_tempfile()
    ok("second tempfile (%s)" % tmppath2, tmppath2 != tmppath)
    ok("second tempfile name == first tempfile name", f.get_filename() == nn)
    f.delete()
    ok("second tempfile deleted", not f.exists())
    
    #get the first tempfile again, rename to original and copy to the original folder
    f = File.File(tmppath)
    ok("again tempfile (%s)" % tmppath, f.exists() and f._is_tempfile() and not f.is_directory())
    f.force_new_filename(i)
    ok("again tempfile filename ok", f.get_filename() == i)
    ok("again tempfile path is local", f.get_local_uri() == tmppath)
    f.transfer(testDir)
    ok("again not tempfile filename ok", f.get_filename() == i)
    if not readOnly: 
        #only makes sense to perform on files that were originally created in 1)
        ok("again not tempfile path matches original", f.get_local_uri() == path)
        ok("again not tempfile mtime ok", f.get_mtime() == mtime)

finished()
