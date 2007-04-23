#common sets up the conduit environment
from common import *

import conduit.Module as Module
import conduit.Utils as Utils
import conduit.datatypes.File as File
import conduit.Conduit as Conduit
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization

import time

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
folder = None
for i in model.get_all_modules():
    if i.classname == "TomboyNoteTwoWay":
        tomboy = model.get_new_module_instance(i.get_key())
    if i.classname == "FolderTwoWay":
        folder = model.get_new_module_instance(i.get_key())

ok("Got Source and Sink", tomboy != None and folder != None)

#configure the folder 
folderDir = os.path.join(os.environ['TEST_DIRECTORY'],"folder")
if not os.path.exists(folderDir):
    os.mkdir(folderDir)

#transfer some tomboy notexml samples to the dir
for i in get_files_from_data_dir("*.tomboy"):
    f = File.File(i)
    f.transfer(folderDir, True)

time.sleep(1)

#configure the source and sink
config = {}
config["folder"] = "file://"+folderDir
config["folderGroupName"] = "Tomboy"
folder.module.set_configuration(config)

#check they refresh ok
try:
    tomboy.module.refresh()
    folder.module.refresh()
    ok("Refresh OK", True)
except Exception, err:
    ok("Refresh OK (%s)" % err, False)

a = tomboy.module.get_num_items()
b = folder.module.get_num_items()
ok("Got items to sync (%s,%s)" % (a,b), a > 0 and b == 0)

#now put them in a conduit and sync
c = Conduit.Conduit()
c.add_dataprovider_to_conduit(tomboy)
c.add_dataprovider_to_conduit(folder)

#SYNC and wait for sync to finish (block)
c.enable_two_way_sync()
sync_manager.sync_conduit(c)
sync_manager.join_all()

#Check the notes were all transferred
#tomboy.module.refresh()
#a = tomboy.module.get_num_items()
#folder.module.refresh()
#b = folder.module.get_num_items()
#ok("All notes transferred (%s,%s)" % (a,b), a == b)

print conduit.mappingDB.debug()
