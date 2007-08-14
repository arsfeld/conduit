#common sets up the conduit environment
from common import *

import conduit
from conduit.datatypes import DataType,COMPARISON_OLDER,COMPARISON_NEWER,COMPARISON_EQUAL,COMPARISON_UNKNOWN
from conduit.DataProvider import TwoWay

import datetime

class TestDataType(conduit.datatypes.DataType.DataType):
    def __init__(self, **kwargs):
        DataType.DataType.__init__(self,"test")
        self.set_UID(
                kwargs.get("data",0)
                )
        self.set_mtime(
                kwargs.get("mtime",datetime.datetime.now())
                )
        
    def compare(self, A, B):
        a = int(A.get_UID())
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
        return TestDataType(data=int(LUID))

    def put(self, data, overwrite, LUID=None):
        TwoWay.put(self, data, overwrite, LUID)
        if LUID != None:
            return LUID
        else:
            return data.get_UID()

    def finish(self): 
        TwoWay.finish(self)

    def get_UID(self):
        return self.uid


test = SimpleSyncTest()
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})

#instantiate directly because we will be manipulating the data directly
source = TestShell(uid="A")
sink = TestShell(uid="B")

test.prepare(
        test.wrap_dataprovider(source), 
        test.wrap_dataprovider(sink)
        )
test.set_two_way_sync(True)

#phase one: add different data to each side
source.added = [1,2,3]
sink.added = [4,5]

a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase two: modify some
source.added = []
source.modified = [4,5]
sink.added = []
sink.modified = [1,2]

a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase two: delete some (delete policy: skip)
source.added = []
source.modified = []
source.deleted = [4]
sink.added = []
sink.modified = []
sink.deleted = [2]

a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase two: delete some (delete policy: ask)
test.set_two_way_policy({"conflict":"skip","deleted":"ask"})
a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase two: delete some (delete policy: replace)
test.set_two_way_policy({"conflict":"skip","deleted":"replace"})
a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase three: modify both (modify policy: skip)
source.added = []
source.modified = [1,5]
source.deleted = []
sink.added = []
sink.modified = [1,5]
sink.deleted = []

test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase three: modify both (modify policy: ask)
#FIXME: BUG. I NEED TO ADD THESE TO MODIFIED AGAIN. THIS SHOWS WE ARE EATING A LIST IN PLACE
source.modified = [1,5]
sink.modified = [1,5]
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)

#phase three: modify both (modify policy: replace)
#FIXME: BUG. I NEED TO ADD THESE TO MODIFIED AGAIN. THIS SHOWS WE ARE EATING A LIST IN PLACE
source.modified = [1,5]
sink.modified = [1,5]
test.set_two_way_policy({"conflict":"replace","deleted":"skip"})
a,b = test.sync(debug=True)
aborted = test.sync_aborted()
ok("Sync completed", aborted == False)
