#common sets up the conduit environment
from common import *

#first conduit, one way, much data, 2 sinks
test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSink")
        )
test.add_extra_sink(
        test.get_dataprovider("TestSink")
        )

config = {}
config["numData"] = 5000
config["errorAfter"] = 10000
test.configure(source=config, sink=config)

#sync
test.set_two_way_sync(False)
test.sync(debug=False)


