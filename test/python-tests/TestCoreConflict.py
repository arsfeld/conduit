#common sets up the conduit environment
from common import *

import conduit.Conflict as Conflict

test = SimpleSyncTest()
test.prepare(
        test.get_dataprovider("TestSource"), 
        test.get_dataprovider("TestConflict")
        )
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
config = {}
config["numData"] = 1
test.configure(source=config)
test.set_two_way_sync(False)

test.sync(debug=False)
aborted,errored,conflicted = test.get_sync_result()
ok("Conflict trapped", conflicted == True and aborted == False)

c = test.conduit._conflicts
ok("One Conflict", len(c) == 1)

test.sync(debug=False)
aborted,errored,conflicted = test.get_sync_result()
ok("Conflict trapped again", conflicted == True and aborted == False)

c = test.conduit._conflicts
ok("Just One Conflict", len(c) == 1)

#get the one conflict
for h,conf in c.items():
    break

resolved = conf.resolve(Conflict.CONFLICT_SKIP)
ok("Didnt resolve when resolution is skip", resolved == False and len(test.conduit._conflicts) == 1)

resolved = conf.resolve(Conflict.CONFLICT_COPY_SOURCE_TO_SINK)
ok("Resolved, source -> sink", resolved == True and len(test.conduit._conflicts) == 0)

finished()