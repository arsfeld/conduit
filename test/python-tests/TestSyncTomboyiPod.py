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

#Set up our own mapping DB so we dont pollute the global one
tempdb = os.path.join
conduit.mappingDB.open_db(os.path.join(os.environ['TEST_DIRECTORY'],Utils.random_string()+".db"))

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = Module.ModuleManager(dirs_to_search)
type_converter = TypeConverter.TypeConverter(model)
sync_manager = Synchronization.SyncManager(type_converter)

tomboy = None
ipod = None
for i in model.get_all_modules():
    if i.classname == "TomboyNoteTwoWay":
        tomboy = model.get_new_module_instance(i.get_key())

#Make a fake iPod so we dont damage a real one
fakeIpodDir = os.path.join(os.environ['TEST_DIRECTORY'],"iPod")
klass = iPodModule.IPodNoteTwoWay(fakeIpodDir,"")
ipod = ModuleWrapper (   
                    getattr(klass, "_name_", ""),
                    getattr(klass, "_description_", ""),
                    getattr(klass, "_icon_", ""),
                    getattr(klass, "_module_type_", ""),
                    None,
                    getattr(klass, "_in_type_", ""),
                    getattr(klass, "_out_type_", ""),
                    'TomboyNoteTwoWay',     #classname
                    [],
                    klass,
                    True
                    )

ok("Created fake ipod at %s" % klass.mountPoint, klass.mountPoint != "")
if not os.path.exists(fakeIpodDir):
    os.mkdir(fakeIpodDir)

ok("Got Source and Sink", tomboy != None and ipod != None)

#check they refresh ok
try:
    tomboy.module.refresh()
    ipod.module.refresh()
    ok("Refresh OK", True)
except Exception, err:
    ok("Refresh OK (%s)" % err, False)

a = tomboy.module.get_num_items()
b = ipod.module.get_num_items()
ok("Got all items to sync (%s,%s)" % (a,b), a > 0 and b == 0)

#now put them in a conduit and sync
c = Conduit.Conduit()
c.add_dataprovider_to_conduit(tomboy)
c.add_dataprovider_to_conduit(ipod)

c.enable_two_way_sync()
sync_manager.sync_conduit(c)

#now wait for sync to finish (block)
sync_manager.join_all()

#Check the notes were all transferred
tomboy.module.refresh()
a = tomboy.module.get_num_items()
ipod.module.refresh()
b = ipod.module.get_num_items()
ok("All notes transferred (%s,%s)" % (a,b), a == b)

print conduit.mappingDB.debug()


