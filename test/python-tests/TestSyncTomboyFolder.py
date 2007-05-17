#common sets up the conduit environment
from common import *

import conduit.datatypes.File as File

import time

test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

#setup the conduit
sourceW = test.get_dataprovider("TomboyNoteTwoWay")
sinkW = test.get_dataprovider("FolderTwoWay")
test.prepare(sourceW, sinkW)

#prepare the test data
folderDir = os.path.join(os.environ['TEST_DIRECTORY'],"folder")
if not os.path.exists(folderDir):
    os.mkdir(folderDir)

for i in get_files_from_data_dir("*.tomboy"):
    f = File.File(i)
    f.transfer(folderDir, True)

time.sleep(1)

#configure the source and sink
config = {}
config["folder"] = "file://"+folderDir
config["folderGroupName"] = "Tomboy"
test.configure(sink=config)

#check they refresh ok
test.refresh()

a = test.get_source_count()
b = test.get_sink_count()
ok("Got items to sync (%s,%s)" % (a,b), a > 0 and b == 0)

#sync
test.set_two_way_sync(True)
test.sync()


#Check the notes were all transferred
#tomboy.module.refresh()
#a = tomboy.module.get_num_items()
#folder.module.refresh()
#b = folder.module.get_num_items()
#ok("All notes transferred (%s,%s)" % (a,b), a == b)

print conduit.mappingDB.debug()
