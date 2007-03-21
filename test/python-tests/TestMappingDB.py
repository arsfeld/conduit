#common sets up the conduit environment
from common import *

import conduit.DB as DB
import conduit.Utils as Utils

import datetime

FILE=os.path.join(os.environ['TEST_DIRECTORY'], "test-%s.db" % Utils.random_string())

m = DB.MappingDB()
m.open_db(FILE)
ok("Create mapping DB (%s)" % FILE, m != None)

now=datetime.datetime.now()

#save some relationships
m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now)
m.save_mapping(sourceUID="source",sourceDataLUID="data3",sinkUID="sink",sinkDataLUID="data4",mtime=now)
m.save_mapping(sourceUID="source",sourceDataLUID="data5",sinkUID="sink",sinkDataLUID="data6",mtime=now)

#check that mapping is saved
ok("Saved all relationships", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
ok("data1 --> data2 for (source --> sink)", luid == "data2" and mtime == now)
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data3",sinkUID="sink")
ok("data3 --> data4 for (source --> sink)", luid == "data4" and mtime == now)

print m.debug()

#check that we never save more than one relationship per dp and uid
m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now)
ok("Duplicate relationships not saved", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

#check that the updated mtime is seved
now2=datetime.datetime.now()
m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now2)
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
ok("Updated mtime saved. data1 --> data2 for (source --> sink)", luid == "data2" and mtime == now2)

m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now2)
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
ok("Duplicate mtime not saved. data1 --> data2 for (source --> sink)", luid == "data2" and mtime == now2)

#check non existant matches
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="foo",sinkUID="bar")
ok("foo --> None for dp", luid == None, mtime == None)

#check that new relationships overwrite old ones
m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="new",mtime=now)
m.save_mapping(sourceUID="source",sourceDataLUID="data3",sinkUID="sink",sinkDataLUID="new",mtime=now)
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink")
ok("New rels overwrite old. data1 --> new for (source --> sink)", luid == "new" and mtime == now)
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data3",sinkUID="sink")
ok("New rels overwrite old. data3 --> new for (source --> sink)", luid == "new" and mtime == now)
ok("New relationships overwrite old", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)

#save some relationships for another dataprovider
m.save_mapping(sourceUID="source",sourceDataLUID="data1",sinkUID="sink2",sinkDataLUID="data2",mtime=now)
m.save_mapping(sourceUID="source",sourceDataLUID="data3",sinkUID="sink2",sinkDataLUID="data4",mtime=now)
m.save_mapping(sourceUID="source2",sourceDataLUID="data1",sinkUID="sink",sinkDataLUID="data2",mtime=now)
m.save_mapping(sourceUID="source2",sourceDataLUID="data3",sinkUID="sink",sinkDataLUID="data4",mtime=now)

print m.debug()

ok("Different dataproviders kept seperate", len(m.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 2)
luid, mtime = m.get_mapping(sourceUID="source", sourceDataLUID="data1",sinkUID="sink2")
ok("Diff DP. data1 --> data2 for (source --> sink2)", luid == "data2" and mtime == now)

#save db to file and restore
m.save()
n = DB.MappingDB()
n.open_db(FILE)
ok("Saved DB loaded", n != None)
ok("Saved DB relationships restored", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink",)) == 3)
ok("Saved DB relationships restored", len(n.get_mappings_for_dataproviders(sourceUID="source",sinkUID="sink2",)) == 2)

print n.debug()
n.save()

