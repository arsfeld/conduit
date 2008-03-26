#common sets up the conduit environment
from common import *

import conduit.datatypes.File as File
import conduit.utils as Utils

#setup the conduit
test = SimpleSyncTest()
sourceW = test.get_dataprovider("TomboyNoteTwoWay")
sinkW = test.get_dataprovider("FolderTwoWay")
test.prepare(sourceW, sinkW)
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})

#check if tomboy running
tomboy = sourceW.module
if not Utils.dbus_service_available(tomboy.TOMBOY_DBUS_IFACE):
    skip("tomboy not running")

#configure the source and sink
config = {}
config["folder"] = "file://"+Utils.new_tempdir()
config["folderGroupName"] = "Tomboy"
test.configure(sink=config)

#check they refresh ok
test.refresh()
a = test.get_source_count()
ok("Got notes to sync (%s)" % a, a > 0)

#sync
test.set_two_way_sync(True)
a,b = test.sync()
abort,error,conflict = test.get_sync_result()
ok("Sync completed", abort == False)
ok("All notes transferred (%s,%s)" % (a,b), a == b)

finished()
