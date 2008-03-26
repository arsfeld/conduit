#common sets up the conduit environment
from common import *

import conduit.MappingDB as MappingDB
import conduit.utils as Utils
from conduit.datatypes import Rid

import datetime

FILE=os.path.join(os.environ['TEST_DIRECTORY'], "test-%s.db" % Utils.random_string())

m = MappingDB.MappingDB(FILE)
ok("Create mapping DB (%s)" % FILE, m != None)

now=datetime.datetime.now()

#save some relationships
i = MappingDB.Mapping(None,sourceUID="source",sourceRid=Rid(uid="data1",mtime=now),sinkUID="sink",sinkRid=Rid(uid="data2",mtime=now))
m.save_mapping(i)
i = MappingDB.Mapping(None,sourceUID="source",sourceRid=Rid(uid="data3",mtime=now),sinkUID="sink",sinkRid=Rid(uid="data4",mtime=now))
m.save_mapping(i)
i = MappingDB.Mapping(None,sourceUID="source",sourceRid=Rid(uid="data5",mtime=now),sinkUID="sink",sinkRid=Rid(uid="data6",mtime=now))
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

#check that the updated mtime is saved correctly
now2=datetime.datetime.now()
now3=datetime.datetime.now()
i = m.get_mapping(sourceUID="source",dataLUID="data1",sinkUID="sink")
i.get_source_rid().mtime = now2
i.get_sink_rid().mtime = now3
m.save_mapping(i)
i = m.get_mapping(sourceUID="source",dataLUID="data1",sinkUID="sink")
ok("Mtimes updated correctly", i.get_source_rid().mtime == now2 and i.get_sink_rid().mtime == now3)
ok("New relationships overwrite old", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

#check non existant matches
i = m.get_mapping(sourceUID="source",dataLUID="foo",sinkUID="bar")
ok("foo --> None for dp", i.oid == None)

#save some relationships for another dataprovider
i = MappingDB.Mapping(None,sourceUID="source",sourceRid=Rid(uid="data1",mtime=now),sinkUID="sink2",sinkRid=Rid(uid="data2",mtime=now))
m.save_mapping(i)
i = MappingDB.Mapping(None,sourceUID="source",sourceRid=Rid(uid="data3",mtime=now),sinkUID="sink2",sinkRid=Rid(uid="data4",mtime=now))
m.save_mapping(i)
#the other way to save new mappings
i = m.get_mapping(sourceUID="source2",dataLUID="data1",sinkUID="sink")
i.get_source_rid().mtime = now
i.get_sink_rid().uid = "data2"
i.get_sink_rid().mtime = now
m.save_mapping(i)
i = m.get_mapping(sourceUID="source2",dataLUID="data3",sinkUID="sink")
i.get_source_rid().mtime = now
i.get_sink_rid().uid = "data4"
i.get_sink_rid().mtime = now
m.save_mapping(i)

ok("Different dataproviders kept seperate", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 2)
i = m.get_mapping(sourceUID="source", dataLUID="data1",sinkUID="sink2")
ok("Diff DP. data1 --> data2 for (source --> sink2)", i.get_sink_rid().uid == "data2" and i.get_sink_rid().mtime == now)

ok("----- MAPPING DB -----", True)
m.debug()

#save db to file and restore
m.save()
m.close()
n = MappingDB.MappingDB(FILE)
ok("Saved DB loaded", n != None)
ok("Saved DB relationships restored", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)
ok("Saved DB relationships restored", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 2)

#delete some mappings
i = n.get_mapping(sourceUID="source",dataLUID="data1",sinkUID="sink")
n.delete_mapping(i)
i = n.get_mapping(sourceUID="source",dataLUID="data3",sinkUID="sink2")
n.delete_mapping(i)

ok("Deleted Mappings", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 1)
ok("Deleted Mappings", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 2)

ok("----- MAPPING DB 2 -----", True)
n.debug()

n.save()
n.close()
finished()

