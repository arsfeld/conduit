#common sets up the conduit environment
from common import *

import conduit.Module as Module
import conduit.utils as Utils
import conduit.datatypes.File as File
import conduit.Conduit as Conduit
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization

from conduit.datatypes import COMPARISON_EQUAL
from conduit.modules.iPodModule import iPodModule

#setup the test
test = SimpleSyncTest()

#Make a fake iPod so we dont damage a real one
fakeIpodDir = os.path.join(os.environ['TEST_DIRECTORY'],"iPod")
if not os.path.exists(fakeIpodDir):
    os.mkdir(fakeIpodDir)
ok("Created fake ipod at %s" % fakeIpodDir, True)
klass = iPodModule.IPodNoteTwoWay(fakeIpodDir,"")

#setup the conduit
sourceW = test.get_dataprovider("TomboyNoteTwoWay")
sinkW = test.wrap_dataprovider(klass)
test.prepare(sourceW, sinkW)
test.set_two_way_policy({"conflict":"replace","deleted":"replace"})

#check if tomboy running
tomboy = sourceW.module
if not Utils.dbus_service_available(tomboy.TOMBOY_DBUS_IFACE):
    skip("tomboy not running")

#check they refresh ok
a,b = test.refresh()
ok("Got all items to sync (%s,%s)" % (a,b), a > 0 and b == 0)

#check they sync ok
a,b = test.sync()
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)
ok("All notes transferred (%s,%s)" % (a,b), a == b)

finished()
