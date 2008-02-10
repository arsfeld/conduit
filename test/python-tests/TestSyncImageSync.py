#common sets up the conduit environment
from common import *

if not is_online():
    skip()

test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("FileSource"), 
        test.get_dataprovider("TestImageSink")
        )
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
test.set_two_way_sync(False)

#add a file
#test.source.module.add("http://files.conduit-project.org/screenshot.png")
test.source.module.add("file:///home/john/image.jpg")
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

finished()
