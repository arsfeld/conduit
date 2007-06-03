#common sets up the conduit environment
from common import *

import conduit.Module as Module
import conduit.Utils as Utils
import conduit.datatypes.File as File
import conduit.Conduit as Conduit
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization

from conduit.datatypes import COMPARISON_EQUAL
from conduit.dataproviders import iPodModule
from conduit.ModuleWrapper import ModuleWrapper

#setup the test
test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"replace","deleted":"replace"})

#Make a fake iPod so we dont damage a real one
fakeIpodDir = os.path.join(os.environ['TEST_DIRECTORY'],"iPod")
if not os.path.exists(fakeIpodDir):
    os.mkdir(fakeIpodDir)
ok("Created fake ipod at %s" % fakeIpodDir, True)
klass = iPodModule.IPodNoteTwoWay(fakeIpodDir,"")

#setup the conduit
tomboy = test.get_dataprovider("TomboyNoteTwoWay")
ipod = test.wrap_dataprovider(klass)
test.prepare(tomboy, ipod)

#check they refresh ok
a,b = test.refresh()
ok("Got all items to sync (%s,%s)" % (a,b), a > 0 and b == 0)

#check they sync ok
a,b = test.sync()
ok("All notes transferred (%s,%s)" % (a,b), a == b)

