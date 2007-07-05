#common sets up the conduit environment
from common import *

import conduit.Utils as Utils
import conduit.datatypes.File as File
from conduit.datatypes import COMPARISON_EQUAL

import traceback
import random
import time

NUM_FILES = 10
GROUP = "TestGroup"

test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"replace","deleted":"replace"})

#setup the conduit
sourceW = test.get_dataprovider("FolderTwoWay")
sinkW = test.get_dataprovider("FolderTwoWay")
test.prepare(sourceW, sinkW)

#prepare the test data
sourceDir = os.path.join(os.environ['TEST_DIRECTORY'],"source")
sinkDir = os.path.join(os.environ['TEST_DIRECTORY'],"sink")
if not os.path.exists(sourceDir):
    os.mkdir(sourceDir)
if not os.path.exists(sinkDir):
    os.mkdir(sinkDir)

FILES = []
for i in range(0, NUM_FILES):
    name = Utils.random_string()
    contents = Utils.random_string()
    f = File.TempFile(contents)
    f.force_new_filename(name)
    #alternate source or sink
    if i % 2 == 0:
        dest = sourceDir
    else:
        dest = sinkDir
    f.transfer(dest, True)
    FILES.append((name,contents))

#create the special files that signify the folders should be synced together
for i in (sourceDir, sinkDir):
    f = File.TempFile(GROUP)
    f.force_new_filename(".conduit.conf")
    f.transfer(i,True)

#configure the source and sink
config = {}
config["folderGroupName"] = GROUP
config["folder"] = "file://"+sourceDir
config["includeHidden"] = False
test.configure(source=config)

config["folder"] = "file://"+sinkDir
test.configure(sink=config)

#check they scan the dirs ok
a = test.get_source_count()
b = test.get_sink_count()
ok("Sync: Got all items (%s,%s,%s)" % (a,b,len(FILES)), (a+b)==len(FILES))

#sync
test.set_two_way_sync(True)
test.sync()

#some IO time
time.sleep(1)

a = test.get_source_count()
b = test.get_sink_count()
ok("Sync: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))


for name,contents in FILES:
    f1 = File.File(os.path.join(sourceDir, name))
    f2 = File.File(os.path.join(sinkDir, name))
    comp = f1.compare(f2)
    ok("Sync: checking source/%s == sink/%s" % (name, name),comp == COMPARISON_EQUAL)

#Now delete half the files
for i in range(0, NUM_FILES/2):
    name, contents = FILES[i]
    #alternate deleting from source or sink
    if i % 2 == 0:
        dest = sourceDir
    else:
        dest = sinkDir

    path = os.path.join(dest, name)
    del(FILES[i])
    os.remove(path)

#some IO time
time.sleep(1)

#SYNC and wait for sync to finish (block)
test.sync()
time.sleep(1)

a = test.get_source_count()
b = test.get_sink_count()
ok("Delete: Files were deleted (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))

for name,contents in FILES:
    f1 = File.File(os.path.join(sourceDir, name))
    f2 = File.File(os.path.join(sinkDir, name))
    comp = f1.compare(f2)
    ok("Delete: checking source/%s == sink/%s" % (name, name),comp == COMPARISON_EQUAL)

#test hidden files and folders
config["folderGroupName"] = GROUP
config["folder"] = "file://"+sourceDir
config["includeHidden"] = True
test.configure(source=config)

config["folder"] = "file://"+sinkDir
test.configure(sink=config)

for i in range(0, NUM_FILES):
    #hidden file
    name = "."+Utils.random_string()
    contents = Utils.random_string()
    f = File.TempFile(contents)
    f.force_new_filename(name)

    #alternate source or sink
    newdir = "."+Utils.random_string()
    if i % 2 == 0:
        dest = os.path.join(sourceDir,newdir)
    else:
        dest = os.path.join(sinkDir,newdir)
    os.mkdir(dest)

    name = os.path.join(dest,name)
    f.transfer(dest, True)
    FILES.append((name,contents))

#SYNC and wait for sync to finish (block)
test.sync()
time.sleep(1)

a = test.get_source_count()
b = test.get_sink_count()
ok("Hidden: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))

