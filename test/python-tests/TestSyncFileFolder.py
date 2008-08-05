#common sets up the conduit environment
from common import *

import conduit.utils as Utils
import conduit.datatypes.File as File
from conduit.datatypes import COMPARISON_EQUAL

import os.path
import traceback
import random
import time

#Repeat syncs a few times to check for duplicate mapping bugs, etc
SYNC_N_TIMES = 3
#Num files to start with
NUM_FILES = 20
#Sleep time for file I/O
SLEEP_TIME = 1
#Print the mapping DB on the last sync?
PRINT_MAPPING_DB = False

#setup test
test = SimpleSyncTest()
sourceW = test.get_dataprovider("FileSource")
sinkW = test.get_dataprovider("FolderTwoWay")
test.prepare(sourceW, sinkW)
test.set_two_way_policy({"conflict":"replace","deleted":"replace"})

#prepare the test data
sourceDir = os.path.join(os.environ['TEST_DIRECTORY'],"filesource")
sourceFolder = os.path.join(os.environ['TEST_DIRECTORY'],"filesourcefolder")
sinkDir = os.path.join(os.environ['TEST_DIRECTORY'],"foldersink")
if not os.path.exists(sourceDir):
    os.mkdir(sourceDir)
if not os.path.exists(sinkDir):
    os.mkdir(sinkDir)
if not os.path.exists(sourceFolder):
    os.mkdir(sourceFolder)


FILES = []

#add some plain files to the dp
for i in range(0, NUM_FILES/2):
    name = Utils.random_string()
    contents = Utils.random_string()
    f = File.TempFile(contents)
    f.force_new_filename(name)
    f.transfer(sourceDir, True)
    FILES.append((name,contents,sourceDir,"",""))
plainFiles = [os.path.join(sourceDir, name) for name,contents,i,j,k in FILES]

#also add a plain folder, containg some more files
FOLDER_GRP_NAME = "i-am-a-folder"
for i in range(0, NUM_FILES/2):
    name = Utils.random_string()
    contents = Utils.random_string()
    f = File.TempFile(contents)
    f.force_new_filename(name)
    f.transfer(sourceFolder, True)
    FILES.append((name,contents,sourceFolder,"",FOLDER_GRP_NAME))

#configure the source
config = {}
config["files"] = plainFiles
config["folders"] = ["file://%s---FIXME---%s" % (sourceFolder,FOLDER_GRP_NAME)]
test.configure(source=config)

#configure the sink
config = {}
config["folder"] = "file://"+sinkDir
test.configure(sink=config)

#check they scan the dirs ok
a = test.get_source_count()
b = test.get_sink_count()
ok("Refresh: Got all items (%s,%s,%s)" % (a,b,len(FILES)), a == len(FILES) and b == 0)

#first try a one way sync
test.set_two_way_sync(False)
for i in range(1,SYNC_N_TIMES+1):
    a,b = test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)

    abort,error,conflict = test.get_sync_result()
    ok("Oneway Sync: Sync #%s completed" % i, abort == False and error == False and conflict == False)
    ok("Oneway Sync: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))

    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    ok("Oneway Sync: %s Mappings source -> sink" % NUM_FILES, len(mapSource2Sink) == NUM_FILES and len(mapSink2Source) == 0)

#two way sync
test.set_two_way_sync(True)
for i in range(1,SYNC_N_TIMES+1):
    a,b = test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)

    abort,error,conflict = test.get_sync_result()
    ok("Sync: Sync #%s completed" % i, abort == False and error == False and conflict == False)
    ok("Sync: Sync all items (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))

    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    ok("Sync: %s Mappings in total", len(mapSource2Sink + mapSink2Source) == NUM_FILES)

#check the plain files
for name,contents,sourceDir,sourceRelPath, sinkRelPath in FILES:
    f1 = File.File(os.path.join(sourceDir, sourceRelPath, name))
    f2 = File.File(os.path.join(sinkDir, sinkRelPath, name))
    comp = f1.compare(f2)
    ok("Sync: checking %s == %s" % (f1._get_text_uri(), f2._get_text_uri()),comp == COMPARISON_EQUAL)

#Now delete half the files
d = []
for i in range(0, NUM_FILES, 2):
    name, contents, sourceDir, sourceRelPath, sinkRelPath = FILES[i]
    path = os.path.join(sourceDir, sourceRelPath, name)
    os.remove(path)
    d.append(FILES[i])
for i in d:
    FILES.remove(i)

#some IO time
time.sleep(SLEEP_TIME)

#SYNC and wait for sync to finish (block)
for i in range(1,SYNC_N_TIMES+1):
    a,b = test.sync(debug = i == SYNC_N_TIMES and PRINT_MAPPING_DB)
    time.sleep(SLEEP_TIME)
    
    abort,error,conflict = test.get_sync_result()
    #There will only be a conflict (delete) the first sync, because the two way policy
    #is to replace the deleted items
    ok("Delete: Sync #%s completed" % i, abort == False and error == False and conflict == (i == 1))
    ok("Delete: Files were deleted (%s,%s,%s)" % (a,b,len(FILES)), a==len(FILES) and b==len(FILES))
    mapSource2Sink = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceW.get_UID(), sinkW.get_UID())
    mapSink2Source = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkW.get_UID(), sourceW.get_UID())
    ok("Delete: %s Mappings in total" % (NUM_FILES/2), len(mapSource2Sink) == (NUM_FILES/2) and len(mapSink2Source) == 0)

for name,contents,sourceDir,sourceRelPath, sinkRelPath in FILES:
    f1 = File.File(os.path.join(sourceDir, sourceRelPath, name))
    f2 = File.File(os.path.join(sinkDir, sinkRelPath, name))
    comp = f1.compare(f2)
    ok("Delete: checking %s == %s" % (f1._get_text_uri(), f2._get_text_uri()),comp == COMPARISON_EQUAL)

finished()
