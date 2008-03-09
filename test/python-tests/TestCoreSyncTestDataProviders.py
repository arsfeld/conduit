#common sets up the conduit environment
from common import *

###
#One way, should error
###
ok("---- ONE WAY: SHOULD ERROR", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSink")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
config = {}
config["numData"] = 5
config["errorAfter"] = 2
test.configure(source=config, sink=config)

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)
error = test.sync_errored()
ok("Non fatal error trapped", error == True)

###
#One way, should abort, but still put data in second sink
###
ok("---- ONE WAY: SHOULD ABORT", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSink")
        )
test.add_extra_sink(
        test.get_dataprovider("TestSink")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
config = {}
config["numData"] = 5
config["errorAfter"] = 2
config["errorFatal"] = True
test.configure(source=config, sink=config)

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

###
#One way, should abort (sink fail refresh)
###
ok("---- ONE WAY: SHOULD ABORT (Sink Fail Refresh)", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestFailRefresh")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync aborted due to no refreshing sinks", aborted == True)

###
#One way, should abort (source fail refresh)
###
ok("---- ONE WAY: SHOULD ABORT (Source Fail Refresh)", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestFailRefresh"),
        test.get_dataprovider("TestSink")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync aborted due to source fail refresh", aborted == True)

###
#One way, should abort (not configured)
###
ok("---- ONE WAY: SHOULD ABORT (Not Configured)", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSinkNeedConfigure")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync aborted due to no configured sinks", aborted == True)

###
#One way, should conflict
###
ok("---- ONE WAY: SHOULD CONFLICT", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestConflict")
        )
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)
conflict = test.sync_conflicted()
ok("Conflict trapped", conflict == True)

###
#Two way
###
ok("---- TWO WAY:", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestTwoWay"), 
        test.get_dataprovider("TestTwoWay")
        )
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})

test.set_two_way_sync(True)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

###
#One way, much data, 2 sinks
###
ok("---- ONE WAY: MUCH DATA", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestSink")
        )
test.add_extra_sink(
        test.get_dataprovider("TestSink")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

config = {}
config["numData"] = 500
config["errorAfter"] = 1000
test.configure(source=config, sink=config)

test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

###
#Test conversion args
###
ok("---- ONE WAY: CONVERSION ARGS", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestConversionArgs")
        )
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
test.set_two_way_sync(False)
test.sync(debug=False)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

###
#Test file and image sink
###
ok("---- ONE WAY: TEST FILE/IMAGE SINK", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestFileSource"), 
        test.get_dataprovider("TestFileSink")
        )
test.add_extra_sink(
        test.get_dataprovider("TestImageSink")
        )
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
test.set_two_way_sync(False)
test.sync(debug=False)
aborted,errored,conflicted = test.get_sync_result()
ok("Sync completed without conflicts", aborted == False and errored == False and conflicted == False)

###
#Test file and image sink
###
ok("---- TWO WAY: TEST FILE", True)
test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestFileTwoWay"), 
        test.get_dataprovider("TestFileTwoWay")
        )
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
test.set_two_way_sync(True)
test.sync(debug=False)
aborted,errored,conflicted = test.get_sync_result()
ok("Sync completed without conflicts", aborted == False and errored == False and conflicted == False)


###
#Test folder sink
###
ok("---- TWO WAY: TEST FILE", True)
test = SimpleSyncTest()
#add a file to source and sink
source = test.get_dataprovider("TestFolderTwoWay")
source.module.add(None)
sink = test.get_dataprovider("TestFolderTwoWay")
sink.module.add(None)
test.prepare(source, sink)
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
test.set_two_way_sync(True)
test.sync(debug=False)
aborted,errored,conflicted = test.get_sync_result()
ok("Sync completed without conflicts", aborted == False and errored == False and conflicted == False)

finished()
