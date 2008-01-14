#common sets up the conduit environment
from common import *

test = SimpleSyncTest()

#Source
source = test.get_dataprovider("TestTwoWay")
netsource = test.networked_dataprovider(source)

#Sink
sink = test.get_dataprovider("TestTwoWay")
netsink = test.networked_dataprovider(sink)

#Sync
test.prepare(
        netsource, 
        sink
        )
test.set_two_way_sync(True)
test.sync(debug=False)
aborted = test.sync_aborted()

ok("Sync completed", aborted == False)

finished()
