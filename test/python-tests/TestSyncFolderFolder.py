#common sets up the conduit environment
from common import *

import conduit.Module as Module
import conduit.Utils as Utils
import conduit.datatypes.File as File
import conduit.Conduit as Conduit
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = Module.ModuleManager(dirs_to_search)
type_converter = TypeConverter.TypeConverter(model)
sync_manager = Synchronization.SyncManager(type_converter)

#sync_manager.set_sync_policy({"conflict":"skip","missing":"skip"})

NUM_FILES = 10
GROUP = "TestGroup"

sourceW = None
sinkW = None
for i in model.get_all_modules():
    if i.classname == "FileTwoWay":
        sourceW = model.get_new_module_instance(i.get_key())
        sinkW = model.get_new_module_instance(i.get_key())

ok("Got Source and Sink", sourceW != None and sinkW != None)

sourceDir = os.path.join(os.environ['TEST_DIRECTORY'],"source")
sinkDir = os.path.join(os.environ['TEST_DIRECTORY'],"sink")
if not os.path.exists(sourceDir):
    os.mkdir(sourceDir)
if not os.path.exists(sinkDir):
    os.mkdir(sinkDir)

FILES = []
#create some random files
for i in range(0, NUM_FILES):
    name = Utils.random_string()
    contents = Utils.random_string()
    f = File.TempFile(contents)
    f.force_new_filename(name)
    #alternate source or sink
    if i % 2 == 0:
        dest = sourceDir
    else:
        dest = sinkDir
    f.transfer(dest, True)
    FILES.append((dest,name,contents))

#create the special files that signify the folders should be synced together
for i in (sourceDir, sinkDir):
    f = File.TempFile(GROUP)
    f.force_new_filename(".conduit.conf")
    f.transfer(i,True)

#configure the source and sink
config = {}
config["unmatchedURI"] = os.environ['HOME']
config["files"] = []
config["folders"] = ["file://"+sourceDir]
sourceW.module.set_configuration(config)
config["folders"] = ["file://"+sinkDir]
sinkW.module.set_configuration(config)

#check they refresh ok
try:
    sinkW.module.refresh()
    sourceW.module.refresh()
    ok("Refresh FileTwoWay", True)
except Exception, err:
    ok("Refresh FileTwoWay (%s)" % err, False)

a = sinkW.module.get_num_items()
b = sourceW.module.get_num_items()
ok("Got all items to sync (%s,%s)" % (a,b), (a+b)==len(FILES))

#now put them in a conduit and sync
conduit = Conduit.Conduit()
conduit.add_dataprovider_to_conduit(sourceW)
conduit.add_dataprovider_to_conduit(sinkW)

conduit.enable_two_way_sync()
sync_manager.sync_conduit(conduit)


