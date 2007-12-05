#common sets up the conduit environment
from common import *

import conduit.Utils as Utils
import conduit.datatypes.File as File
from conduit.datatypes import COMPARISON_EQUAL

import traceback
import random
import time

#Repeat syncs a few times to check for duplicate mapping bugs, etc
SYNC_N_TIMES = 3
#Num files to start with, should end with 150% of this number
NUM_FILES = 10
#Sleep time for file I/O
SLEEP_TIME = 1
#Print the mapping DB on the last sync?
PRINT_MAPPING_DB = True

#setup test
test = SimpleSyncTest()
sourceW = test.get_dataprovider("FolderTwoWay")
sinkW = test.get_dataprovider("FolderTwoWay")
test.prepare(sourceW, sinkW)
test.set_two_way_policy({"conflict":"replace","deleted":"replace"})

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

#configure the source and sink
config = {}
config["folderGroupName"] = "TestGroup"
config["folder"] = "file://"+sourceDir
config["includeHidden"] = False
test.configure(source=config)

config["folder"] = "file://"+sinkDir
test.configure(sink=config)

#check they scan the dirs ok
a = test.get_source_count()
b = test.get_sink_count()
ok("Refresh: Got all items (%s,%s,%s)" % (a,b,len(FILES)), (a+b)==len(FILES))

#first try a one way sync
test.set_two_way_sync(False)
for i in range(1,SYNC_N_TIMES+1):
    test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)

    abort,error,conflict = test.get_sync_result()
    ok("Oneway Sync: Sync #%s completed" % i, abort == False and error == False and conflict == False)

    a = test.get_source_count()
    b = test.get_sink_count()
    ok("Oneway Sync: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES)/2 and b==len(FILES))

    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    print mapSource2Sink, mapSink2Source
    ok("Oneway Sync: 5 Mappings source -> sink", len(mapSource2Sink) == 5 and len(mapSink2Source) == 0)

#two way sync
test.set_two_way_sync(True)
for i in range(1,SYNC_N_TIMES+1):
    test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)

    abort,error,conflict = test.get_sync_result()
    ok("Sync: Sync #%s completed" % i, abort == False and error == False and conflict == False)

    a = test.get_source_count()
    b = test.get_sink_count()
    ok("Sync: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))

    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    ok("Sync: 10 Mappings in total", len(mapSource2Sink + mapSink2Source) == 10)

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
time.sleep(SLEEP_TIME)

#SYNC and wait for sync to finish (block)
for i in range(1,SYNC_N_TIMES+1):
    test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)
    
    abort,error,conflict = test.get_sync_result()
    #There will only be a conflict (delete) the first sync, because the two way policy
    #is to replace the deleted items
    ok("Delete: Sync #%s completed" % i, abort == False and error == False and conflict == (i == 1))

    a = test.get_source_count()
    b = test.get_sink_count()
    ok("Delete: Files were deleted (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))
    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    ok("Delete: 5 Mappings in total", len(mapSource2Sink + mapSink2Source) == 5)


for name,contents in FILES:
    f1 = File.File(os.path.join(sourceDir, name))
    f2 = File.File(os.path.join(sinkDir, name))
    comp = f1.compare(f2)
    ok("Delete: checking source/%s == sink/%s" % (name, name),comp == COMPARISON_EQUAL)

#test hidden files and folders
config["folderGroupName"] = "TestGroup"
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

for i in range(1,SYNC_N_TIMES+1):
    test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)
    
    abort,error,conflict = test.get_sync_result()
    ok("Hidden: Sync #%s completed" % i, abort == False and error == False and conflict == False)

    a = test.get_source_count()
    b = test.get_sink_count()
    ok("Hidden: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))
    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    ok("Hidden: 15 Mappings in total", len(mapSource2Sink + mapSink2Source) == 15)

finished()
