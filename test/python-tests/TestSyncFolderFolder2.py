#common sets up the conduit environment
from common import *

import conduit.datatypes.File as File

import os
import tempfile

#test overwriting older files with newer ones
FILENAME = "%s/testfile"
CONTENTS = "foo"
CONTENTS_NEW = "foo bar"
SLEEP_TIME = 1

def setup_folder_dps():
    frmdir = tempfile.mkdtemp()
    todir = tempfile.mkdtemp()

    test = SimpleSyncTest()
    test.prepare(
            test.get_dataprovider("FolderTwoWay"),
            test.get_dataprovider("FolderTwoWay"))
    test.set_two_way_policy({"conflict":"ask","deleted":"ask"})

    config = {}
    config["folderGroupName"] = "TestGroup"
    config["folder"] = "file://"+frmdir
    config["includeHidden"] = False
    config["followSymlinks"] = False
    test.configure(source=config)

    config["folder"] = "file://"+todir
    test.configure(sink=config)
    return test, frmdir, todir

########################################
# Test overwrite an older file with an updated one
########################################
test, frmdir, todir = setup_folder_dps()

#write test file
fa = open(FILENAME % frmdir, 'w')
fa.write(CONTENTS)
fa.close()

test.sync()
time.sleep(SLEEP_TIME)
abort,error,conflict = test.get_sync_result()
ok("Sync OK", abort == False and error == False and conflict == False)

fb = open(FILENAME % todir, 'r')
ok("File transferred", fb.read() == CONTENTS)
fb.close()

#mod test file
time.sleep(SLEEP_TIME)
fa = open(FILENAME % frmdir, 'w')
fa.write(CONTENTS_NEW)
fa.close()

test.sync()
time.sleep(SLEEP_TIME)
abort,error,conflict = test.get_sync_result()
ok("Sync OK", abort == False and error == False and conflict == False)

fb = open(FILENAME % todir, 'r')
ok("Updated File transferred", fb.read() == CONTENTS_NEW)
fb.close()

########################################
# Putting an older file over an unknown new one shoud conflict
########################################
test, frmdir, todir = setup_folder_dps()

#write test files
fa = open(FILENAME % frmdir, 'w')
fa.write(CONTENTS)
fa.close()

#diff mtime
time.sleep(SLEEP_TIME*2)

fa = open(FILENAME % todir, 'w')
fa.write(CONTENTS)
fa.close()

test.sync()
abort,error,conflict = test.get_sync_result()
ok("Detected conflict on existing file", abort == False and error == False and conflict == True)

########################################
# Putting a file over an unknown new one with the same mtime, but diff size
# should conflict
########################################
test, frmdir, todir = setup_folder_dps()

#write test files
faName = FILENAME % frmdir
fa = open(faName, 'w')
fa.write(CONTENTS)
fa.close()

fbName = FILENAME % todir
fb = open(fbName, 'w')
fb.write(CONTENTS_NEW)
fb.close()

#make fb same mtime as fa, yuck!
os.system("touch %s -r %s" % (fbName, faName))

a = File.File(URI=faName)
b = File.File(URI=fbName)
compSize = a.compare(b, sizeOnly=True)
ok("Files different size", compSize == conduit.datatypes.COMPARISON_UNKNOWN)

compSize = a.compare(b, sizeOnly=False)
ok("Files same mtime, and different size", compSize == conduit.datatypes.COMPARISON_UNKNOWN)

test.sync(debug=False)
abort,error,conflict = test.get_sync_result()
ok("Detected conflict on existing file, same mtime, diff size", abort == False and error == False and conflict == True)

########################################
# Putting a file over an unknown new one with the same mtime, and same size
# wont conflict, we cant do any stronger tests without hashing
########################################
test, frmdir, todir = setup_folder_dps()

#write test files
faName = FILENAME % frmdir
fa = open(faName, 'w')
fa.write(CONTENTS)
fa.close()

fbName = FILENAME % todir
fb = open(fbName, 'w')
fb.write(CONTENTS)
fb.close()

#make fb same mtime as fa, yuck!
os.system("touch %s -r %s" % (fbName, faName))

a = File.File(URI=faName)
b = File.File(URI=fbName)
compSize = a.compare(b, sizeOnly=True)
ok("Files same size", compSize == conduit.datatypes.COMPARISON_EQUAL)

compSize = a.compare(b, sizeOnly=False)
ok("Files same mtime, and same size", compSize == conduit.datatypes.COMPARISON_EQUAL)

test.sync(debug=False)
abort,error,conflict = test.get_sync_result()
ok("No conflict for existing same files", abort == False and error == False and conflict == False)

finished()

