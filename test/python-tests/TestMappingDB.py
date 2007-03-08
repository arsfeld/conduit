#common sets up the conduit environment
from common import *

import conduit.DB as DB
import conduit.Utils as Utils

FILE=os.path.join(os.environ['TEST_DIRECTORY'], "test-%s.db" % Utils.random_string())

m = DB.MappingDB(FILE)
ok("Create mapping DB", m != None)

#save some relationships
m.save_relationship("dp","data1","data2")
m.save_relationship("dp","data3","data4")
m.save_relationship("dp","data5","data6")

#check that mapping is saved
ok("Saved all relationships", len(m._get_relationships("dp")) == 3)
ok("data1 --> data2 for dp", m.get_matching_uid("dp","data1") == "data2")
ok("data3 --> data4 for dp", m.get_matching_uid("dp","data3") == "data4")

m.debug()

#check that we never save more than one relationship per dp and uid
m.save_relationship("dp","data1","data2")
ok("Duplicate relationships not saved", len(m._get_relationships("dp")) == 3)

#check non existant matches
ok("foo --> None for dp", m.get_matching_uid("dp","foo") == None)

#check that new relationships overwrite old ones
m.save_relationship("dp","data1","new")
m.save_relationship("dp","data3","new")
ok("New relationships data1 --> new overwrite old", m.get_matching_uid("dp","data1") == "new")
ok("New relationships data3 --> new overwrite old", m.get_matching_uid("dp","data3") == "new")
ok("New relationships overwrite old", len(m._get_relationships("dp")) == 3)

#save some relationships for another dataprovider
m.save_relationship("dp2","data1","data2")
m.save_relationship("dp2","data3","data4")
ok("Different dataproviders kept seperate", len(m._get_relationships("dp2")) == 2)
ok("Different dataproviders data5 --> data6 for dp", m.get_matching_uid("dp","data5") == "data6")
ok("Different dataproviders data5 --> None for dp2", m.get_matching_uid("dp2","data5") == None)
ok("Different dataproviders data1 --> new for dp", m.get_matching_uid("dp","data1") == "new")
ok("Different dataproviders data1 --> data2 for dp2", m.get_matching_uid("dp2","data1") == "data2")

#save db to file and restore
m.save()
n = DB.MappingDB(FILE)
ok("Saved DB loaded", n != None)
ok("Saved DB relationships restored", len(n._get_relationships("dp")) == 3)
ok("Saved DB relationships restored", len(n._get_relationships("dp2")) == 2)

n.debug()
n.save()

