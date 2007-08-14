#common sets up the conduit environment
from common import *

###
#One way, should error
###
ok("---- ONE WAY: SHOULD ERROR", True)
test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSink")
        )
config = {}
config["numData"] = 5
config["errorAfter"] = 2
test.configure(source=config, sink=config)

test.set_two_way_sync(False)
test.sync(debug=False)
error = test.sync_errored()
ok("Non fatal error trapped", error == True)

###
#One way, should abort (fail refresh)
###
ok("---- ONE WAY: SHOULD ABORT (Fail Refresh)", True)
test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSinkFailRefresh")
        )

test.set_two_way_sync(False)
test.sync(debug=False, die=False)
aborted = test.sync_aborted()
ok("Sync aborted due to no refreshing sinks", aborted == True)

###
#One way, should conflict
###
ok("---- ONE WAY: SHOULD CONFLICT", True)
test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestConflict")
        )

test.set_two_way_sync(False)
test.sync(debug=False)
conflict = test.sync_conflicted()
ok("Conflict trapped", conflict == True)

###
#Two way
###
ok("---- TWO WAY:", True)
test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
test.prepare(
        test.get_dataprovider("TestTwoWay"), 
        test.get_dataprovider("TestTwoWay")
        )

test.set_two_way_sync(True)
test.sync(debug=False)

###
#One way, much data, 2 sinks
###
ok("---- ONE WAY: MUCH DATA", True)
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
config["numData"] = 500
config["errorAfter"] = 1000
test.configure(source=config, sink=config)

test.set_two_way_sync(False)
test.sync(debug=False)
