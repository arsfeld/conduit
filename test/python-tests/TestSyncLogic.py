#common sets up the conduit environment
from common import *

import conduit
from conduit.datatypes import DataType,COMPARISON_OLDER,COMPARISON_NEWER,COMPARISON_EQUAL,COMPARISON_UNKNOWN
from conduit.dataproviders.DataProvider import TwoWay

import datetime

class TestDataType(conduit.datatypes.DataType.DataType):
    _name_ = "test"
    def __init__(self, **kwargs):
        DataType.DataType.__init__(self)
        self.set_UID(
                kwargs.get("data",'0')
                )
        self.set_mtime(
                kwargs.get("mtime",datetime.datetime.now())
                )
                
    def get_hash(self):
        return "pipe"
                
    def compare(self, B):
        a = int(self.get_UID())
        b = int(B.get_UID())
        if a < b:
            return COMPARISON_OLDER
        elif a > b:
            return COMPARISON_NEWER
        elif a == b:
            return COMPARISON_EQUAL
        else:
            return COMPARISON_UNKNOWN

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
        return TestDataType(data=LUID)

    def put(self, data, overwrite, LUID=None):
        TwoWay.put(self, data, overwrite, LUID)
        newData = TestDataType(data=data.get_UID())
        return newData.get_rid()        

    def finish(self): 
        TwoWay.finish(self)

    def get_UID(self):
        return self.uid

def get_mappings(sourceDpw, sinkDpw):
    mappings = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sourceDpw.get_UID(), sinkDpw.get_UID())
    mappings += conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(sinkDpw.get_UID(), sourceDpw.get_UID())
    return mappings

test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

#instantiate directly because we will be manipulating the data directly
source = TestShell(uid="A")
sourceDpw = test.wrap_dataprovider(source)
sink = TestShell(uid="B")
sinkDpw = test.wrap_dataprovider(sink)

test.prepare(
        test.wrap_dataprovider(source), 
        test.wrap_dataprovider(sink)
        )
test.set_two_way_sync(True)

#phase one: add different data to each side
source.added = ['1','2','3']
sink.added = ['4','5']

a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase one: add different data to each side", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("5 mappings exist", len(mappings) == 5)

#phase two: modify some
source.added = []
source.modified = ['4','5']
sink.added = []
sink.modified = ['1','2']

a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase two: modify some", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("5 mappings exist", len(mappings) == 5)

#phase two: delete some (delete policy: skip)
source.added = []
source.modified = []
source.deleted = ['4']
sink.added = []
sink.modified = []
sink.deleted = ['2']

a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase two: delete some (delete policy: skip)", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("5 mappings exist", len(mappings) == 5)

#phase two: delete some (delete policy: ask)
test.set_two_way_policy({"conflict":"skip","deleted":"ask"})
a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase two: delete some (delete policy: ask)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("5 mappings exist", len(mappings) == 5)

#phase two: delete some (delete policy: replace)
test.set_two_way_policy({"conflict":"skip","deleted":"replace"})
a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase two: delete some (delete policy: replace)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("3 mappings exist", len(mappings) == 3)

#phase three: modify both (modify policy: skip)
source.added = []
source.modified = ['1','5']
source.deleted = []
sink.added = []
sink.modified = ['1','5']
sink.deleted = []

test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase three: modify both (modify policy: skip)", abort == False and error == False and conflict == False)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("3 mappings exist", len(mappings) == 3)

#phase three: modify both (modify policy: ask)
source.modified = ['1','5']
sink.modified = ['1','5']
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase three: modify both (modify policy: ask) %s,%s,%s" % (abort,error,conflict), abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("3 mappings exist", len(mappings) == 3)

#phase three: modify both (modify policy: replace)
source.modified = ['1','5']
sink.modified = ['1','5']
test.set_two_way_policy({"conflict":"replace","deleted":"skip"})
a,b = test.sync(debug=True)
abort,error,conflict = test.get_sync_result()
ok("Sync completed: phase three: modify both (modify policy: replace)", abort == False and error == False and conflict == True)
mappings = get_mappings(sourceDpw, sinkDpw)
ok("3 mappings exist", len(mappings) == 3)

finished()
