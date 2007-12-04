#common sets up the conduit environment
from common import *

import conduit
from conduit.datatypes import DataType,COMPARISON_OLDER,COMPARISON_NEWER,COMPARISON_EQUAL,COMPARISON_UNEQUAL
from conduit.dataproviders.DataProvider import TwoWay

import datetime

class TestDataType(conduit.datatypes.DataType.DataType):
    _name_ = "test"
    def __init__(self, data, **kwargs):
        """
        Data is a 2 numeric char string. The first char is the
        UID of the data, and the second is a day past my bday
        e.g.
        10 -> uid=1, mtime - 16/8/1983
        72 -> uid=7, mtime - 18/8/1983   
        """
        DataType.DataType.__init__(self)
        assert(len(data) == 2)
        self.data = data
        self.set_UID(data[0])
        self.set_mtime(datetime.datetime(1983,8,16+int(data[1])))
                
    def get_hash(self):
        return hash( self.get_mtime() )
                
class TestShell(TwoWay):
    _module_type_ = "twoway"
    _in_type_ = "test"
    _out_type_ = "test"

    def __init__(self, uid):
        TwoWay.__init__(self)
        self.uid = uid

        self.added = []
        self.modified = []
        self.deleted = []
        
        self.LUID_mtimes = {}
        
        self.num_put = 0
        self.num_del = 0
        
    def initialize(self):
        return True

    def refresh(self):
        TwoWay.refresh(self)

    def get_changes(self):
        return self.added, self.modified, self.deleted

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.added) + len(self.modified) + len(self.deleted)

    def get(self, LUID):
        return TestDataType(LUID+self.LUID_mtimes.get(LUID,'0'))

    def put(self, data, overwrite, LUID=None):
        TwoWay.put(self, data, overwrite, LUID)
        self.num_put += 1
        newData = TestDataType(data.data)
        return newData.get_rid()
        
    def delete(self, LUID):
        self.num_del += 1
        return True

    def get_UID(self):
        return self.uid

def get_mappings(sourceDpw, sinkDpw):
    mappings = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceDpw.get_UID(), sinkDpw.get_UID())
    mappings += conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkDpw.get_UID(), sourceDpw.get_UID())
    return mappings
    
def reset_dataproviders(source, sink):
    source.num_put = 0
    source.num_del = 0
    sink.num_put = 0
    sink.num_del = 0
    source.added = []
    source.modified = []
    source.deleted = []
    sink.added = []
    sink.modified = []
    sink.deleted = []
    
#print out the mapping DB each sync?
DB_DEBUG = False

#instantiate directly because we will be manipulating the data directly
source = TestShell(uid="A")
sink = TestShell(uid="B")

test = SimpleSyncTest()
sourceDpw = test.wrap_dataprovider(source)
sinkDpw = test.wrap_dataprovider(sink)
test.prepare(
        sourceDpw, 
        sinkDpw
        )
test.set_two_way_sync(True)

################################################################################
# Test The Datatype and comparison methods
################################################################################
a = TestDataType('10')
ok("Prep: Test a datatype UID ok", a.get_UID() == '1')
ok("Prep: Test a mtime ok", a.get_mtime() == datetime.datetime(1983,8,16))

b = TestDataType('42')
ok("Prep: Test b datatype UID ok", b.get_UID() == '4')
ok("Prep: Test b mtime ok", b.get_mtime() == datetime.datetime(1983,8,18))

ok("Prep: Test a older than b", a.compare(b) == COMPARISON_OLDER)
ok("Prep: Test b newer than a", b.compare(a) == COMPARISON_NEWER)

c = TestDataType('10')
ok("Prep: Test c equal to a", a.compare(c) == COMPARISON_EQUAL)

d = TestDataType('99')
d.set_mtime(None)
ok("Prep: Test d unequal to a", a.compare(d) == COMPARISON_UNEQUAL)

################################################################################
# TWO WAY SYNC WITH ONE SOURCE AND ONE SINK
################################################################################
#phase one: add different data to each side
reset_dataproviders(source, sink)
source.added = ['1','2','3']
sink.added = ['4','5']

a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase one: add different data to each side", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 5 mappings exist", len(mappings) == 5)
ok("2Way: 3x data put into sink", sink.num_put == 3 and sink.num_del == 0)
ok("2Way: 2x data put into source", source.num_put == 2 and source.num_del == 0)

#phase two: modify some
reset_dataproviders(source, sink)
source.modified = ['4','5']
sink.modified = ['1','2']

a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase two: modify some", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 5 mappings exist", len(mappings) == 5)
ok("2Way: 2x data put into sink", sink.num_put == 2 and sink.num_del == 0)
ok("2Way: 2x data put into source", source.num_put == 2 and source.num_del == 0)

#phase two: delete some (delete policy: skip)
reset_dataproviders(source, sink)
source.deleted = ['4']
sink.deleted = ['2']

a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase two: delete some (delete policy: skip)", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 5 mappings exist", len(mappings) == 5)
ok("2Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 0x data del from source", source.num_put == 0 and source.num_del == 0)

#phase two: delete some (delete policy: ask)
test.set_two_way_policy({"conflict":"skip","deleted":"ask"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase two: delete some (delete policy: ask)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 5 mappings exist", len(mappings) == 5)
ok("2Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 0x data del from source", source.num_put == 0 and source.num_del == 0)

#phase two: delete some (delete policy: replace)
test.set_two_way_policy({"conflict":"skip","deleted":"replace"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase two: delete some (delete policy: replace)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 3 mappings exist", len(mappings) == 3)
ok("2Way: 1x data del from sink", sink.num_put == 0 and sink.num_del == 1)
ok("2Way: 1x data del from source", source.num_put == 0 and source.num_del == 1)

#phase three: modify both (modify policy: skip)
reset_dataproviders(source, sink)
source.modified = ['1','5']
#make source data 1 newer than sink data 1
source.LUID_mtimes['1'] = '1'
sink.modified = ['1','5']
#make sink data 5 newer than source data 5
sink.LUID_mtimes['5'] = '1'

test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase three: modify both (modify policy: skip)", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 3 mappings exist", len(mappings) == 3)
ok("2Way: 0x data put from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 0x data put from source", source.num_put == 0 and source.num_del == 0)

#phase three: modify both (modify policy: ask)
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase three: modify both (modify policy: ask) %s,%s,%s" % (abort,error,conflict), abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 3 mappings exist", len(mappings) == 3)
ok("2Way: 0x data put from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 0x data put from source", source.num_put == 0 and source.num_del == 0)

#phase three: modify both (modify policy: replace)
test.set_two_way_policy({"conflict":"replace","deleted":"skip"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase three: modify both (modify policy: replace)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 3 mappings exist", len(mappings) == 3)
ok("2Way: 1x data put from sink", sink.num_put == 1 and sink.num_del == 0)
ok("2Way: 1x data put from source", source.num_put == 1 and source.num_del == 0)

#phase four: test mod and delete (delete policy: skip)
reset_dataproviders(source, sink)
source.modified = ['3']
sink.deleted = ['3']

a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase four: mod+del (delete policy: skip)", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 3 mappings exist", len(mappings) == 3)
ok("2Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 0x data del from source", source.num_put == 0 and source.num_del == 0)

#phase four: test mod and delete (delete policy: ask)
test.set_two_way_policy({"conflict":"skip","deleted":"ask"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase four: mod+del (delete policy: ask)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 3 mappings exist", len(mappings) == 3)
ok("2Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 0x data del from source", source.num_put == 0 and source.num_del == 0)

#phase four: test mod and delete (delete policy: replace)
test.set_two_way_policy({"conflict":"skip","deleted":"replace"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("2Way: Sync completed: phase four: mod+del (delete policy: replace)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("2Way: 2 mappings exist", len(mappings) == 2)
ok("2Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)
ok("2Way: 1x data del from source", source.num_put == 0 and source.num_del == 1)

################################################################################
# ONE WAY SYNC WITH ONE SOURCE AND ONE SINK
################################################################################
conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceDpw.get_UID(), sinkDpw.get_UID())
sourceDpw.module_type = "source"
sinkDpw.module_type = "sink"
test.prepare(
        sourceDpw, 
        sinkDpw
        )
test.set_two_way_sync(False)

#phase one: add data
reset_dataproviders(source, sink)
source.added = ['1','2','3','4','5']

a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("1Way: Sync completed: phase one: add data", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("1Way: 5 mappings exist", len(mappings) == 5)
ok("1Way: 5x data put into sink", sink.num_put == 5 and sink.num_del == 0)

#phase two: mod data
reset_dataproviders(source, sink)
source.modified = ['1','2','3']

a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("1Way: Sync completed: phase two: mod data", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("1Way: 5 mappings exist", len(mappings) == 5)
ok("1Way: 3x data put into sink", sink.num_put == 3 and sink.num_del == 0)

#phase three: delete data
reset_dataproviders(source, sink)
source.deleted = ['1','2','3']

test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("1Way: Sync completed: phase three: delete data (delete policy: skip)", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("1Way: 5 mappings exist", len(mappings) == 5)
ok("1Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)

test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("1Way: Sync completed: phase three: delete data (delete policy: ask)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("1Way: 5 mappings exist", len(mappings) == 5)
ok("1Way: 0x data del from sink", sink.num_put == 0 and sink.num_del == 0)

test.set_two_way_policy({"conflict":"ask","deleted":"replace"})
a,b = test.sync(debug=DB_DEBUG)
abort,error,conflict = test.get_sync_result()
ok("1Way: Sync completed: phase three: delete data (delete policy: replace)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("1Way: 2 mappings exist", len(mappings) == 2)
ok("1Way: 3x data del from sink", sink.num_put == 0 and sink.num_del == 3)

finished()
