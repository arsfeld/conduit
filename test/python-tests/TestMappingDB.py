#common sets up the conduit environment
from common import *

import conduit.MappingDB as MappingDB
import conduit.Utils as Utils

import datetime

FILE=os.path.join(os.environ['TEST_DIRECTORY'], "test-%s.db" % Utils.random_string())

m = MappingDB.MappingDB()
m.open_db(FILE)
ok("Create mapping DB (%s)" % FILE, m != None)

now=datetime.datetime.now()

#save some relationships
i = MappingDB.Mapping(None,sourceUID="source",sourceDataLUID="data1",sourceDataMtime=now,sinkUID="sink",sinkDataLUID="data2",sinkDataMtime=now)
m.save_mapping(i)
i = MappingDB.Mapping(None,sourceUID="source",sourceDataLUID="data3",sourceDataMtime=now,sinkUID="sink",sinkDataLUID="data4",sinkDataMtime=now)
m.save_mapping(i)
i = MappingDB.Mapping(None,sourceUID="source",sourceDataLUID="data5",sourceDataMtime=now,sinkUID="sink",sinkDataLUID="data6",sinkDataMtime=now)
m.save_mapping(i)

#check that mapping is saved
ok("Saved all relationships", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

luid = m.get_matching_UID(sourceUID="source", dataLUID="data1",sinkUID="sink")
ok("data1 --> data2 for (source --> sink)", luid == "data2")
luid = m.get_matching_UID(sourceUID="source", dataLUID="data2",sinkUID="sink")
ok("data2 --> data1 for (source --> sink)", luid == "data1")
luid = m.get_matching_UID(sourceUID="sink", dataLUID="data1",sinkUID="source")
ok("data1 --> data2 for (sink --> source)", luid == "data2")
luid = m.get_matching_UID(sourceUID="sink", dataLUID="data2",sinkUID="source")
ok("data2 --> data1 for (sink --> source)", luid == "data1")

luid = m.get_matching_UID(sourceUID="source", dataLUID="data3",sinkUID="sink")
ok("data3 --> data4 for (source --> sink)", luid == "data4")


#check that we never save more than one relationship per dp and uid
#m.save_mapping(sourceUID="source",sourceDataLUID="data1",sourceDataMtime=now,sinkUID="sink",sinkDataLUID="data2",sinkDataMtime=now)
#ok("Duplicate relationships not saved", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

#check that the updated mtime is saved correctly for both dps in both directions
now2=datetime.datetime.now()
i = m.get_mapping(sourceUID="source",dataLUID="data1",sinkUID="sink")
i["sourceDataMtime"] = now2
m.save_mapping(i)

ok("Mtimes updated correctly", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)
print m.debug()

raise

# luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
# ok("Updated mtime saved. data1 --> data2 for (source --> sink)", luid == "data2" and mtime == now2)

# m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now2)
# luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
# ok("Duplicate mtime not saved. data1 --> data2 for (source --> sink)", luid == "data2" and mtime == now2)

# #check non existant matches
# luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="foo",sinkUID="bar")
# ok("foo --> None for dp", luid == None, mtime == None)

# #check that new relationships overwrite old ones
# m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="new",mtime=now)
# m.save_mapping(sourceUID="source",sourceDataLUID="data3",sinkUID="sink",sinkDataLUID="new",mtime=now)
# luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
# ok("New rels overwrite old. data1 --> new for (source --> sink)", luid == "new" and mtime == now)
# luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data3",sinkUID="sink")
# ok("New rels overwrite old. data3 --> new for (source --> sink)", luid == "new" and mtime == now)
# ok("New relationships overwrite old", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

# #save some relationships for another dataprovider
# m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink2",sinkDataLUID="data2",mtime=now)
# m.save_mapping(sourceUID="source",sourceDataLUID="data3",sinkUID="sink2",sinkDataLUID="data4",mtime=now)
# m.save_mapping(sourceUID="source2",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now)
# m.save_mapping(sourceUID="source2",sourceDataLUID="data3",sinkUID="sink",sinkDataLUID="data4",mtime=now)

# print m.debug()

# ok("Different dataproviders kept seperate", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 2)
# luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink2")
# ok("Diff DP. data1 --> data2 for (source --> sink2)", luid == "data2" and mtime == now)

#save db to file and restore
m.save()
n = MappingDB.MappingDB()
n.open_db(FILE)
ok("Saved DB loaded", n != None)
ok("Saved DB relationships restored", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)
#ok("Saved DB relationships restored", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 2)

print n.debug()

#delete some mappings
n.delete_mapping(sourceUID="source",dataLUID="data1",sinkUID="sink")
#n.delete_mapping(sourceUID="source",dataLUID="data3",sinkUID="sink2")

#ok("Deleted Mappings", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 1)
ok("Deleted Mappings", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 2)

print n.debug()

n.save()

finished()
