#common sets up the conduit environment
from common import *

import conduit
from conduit.datatypes import DataType,COMPARISON_OLDER,COMPARISON_NEWER,COMPARISON_EQUAL, COMPARISON_UNKNOWN
from conduit.dataproviders.DataProvider import TwoWay

import datetime

class TestDataType(DataType.DataType):
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

    def get_all(self):
        return self.added + self.modified

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

def sync_and_check_result(name,description,test,expectedResult,expectedMappings, **kwargs):
    sex = kwargs.get("sourceExpects", ())
    skex = kwargs.get("sinkExpects", ())
    sdpw = test.get_source()
    skdpw = test.get_sink()
    #peform the sync
    test.sync(debug=DB_DEBUG)
    a,e,c = test.get_sync_result()
    ok("%s: Result OK (%s)" % (name,description), (a,e,c) == expectedResult)
    #check we stored all the expected mappings
    mappings = get_mappings(sdpw, skdpw)
    ok("%s: %s mappings exist" % (name,expectedMappings), len(mappings) == expectedMappings)
    #check the data was transferred in the right direction
    if sex:
        ok("%s: Source: put=%s del=%s" % (name,sex[0],sex[1]), sdpw.module.num_put == sex[0] and sdpw.module.num_del == sex[1])
    if skex:
        ok("%s: Sink: put=%s del=%s" % (name,skex[0],skex[1]), skdpw.module.num_put == skex[0] and skdpw.module.num_del == skex[1])

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
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
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
ok("Prep: Test d unknown comparison with a", a.compare(d) == COMPARISON_UNKNOWN)

################################################################################
# TWO WAY SYNC WITH ONE SOURCE AND ONE SINK
################################################################################
#phase one: add different data to each side
reset_dataproviders(source, sink)
source.added = ['1','2','3']
sink.added = ['4','5']
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
sync_and_check_result(
        name="2Way",
        description="add data",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=5,
        sinkExpects=(3,0),
        sourceExpects=(2,0))

#phase two: modify some
reset_dataproviders(source, sink)
source.modified = ['4','5']
sink.modified = ['1','2']
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
sync_and_check_result(
        name="2Way",
        description="modify some (no conflicts)",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=5,
        sinkExpects=(2,0),
        sourceExpects=(2,0))

#phase two: delete some (delete policy: skip)
reset_dataproviders(source, sink)
source.deleted = ['4']
sink.deleted = ['2']
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
sync_and_check_result(
        name="2Way",
        description="delete some (delete policy: skip)",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=5,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

#phase two: delete some (delete policy: ask)
test.set_two_way_policy({"conflict":"skip","deleted":"ask"})
sync_and_check_result(
        name="2Way",
        description="delete some (delete policy: ask)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=5,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

#phase two: delete some (delete policy: replace)
test.set_two_way_policy({"conflict":"skip","deleted":"replace"})
sync_and_check_result(
        name="2Way",
        description="delete some (delete policy: replace)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=3,
        sinkExpects=(0,1),
        sourceExpects=(0,1))

#phase three: modify both (modify policy: skip)
reset_dataproviders(source, sink)
source.modified = ['1','5']
#make source data 1 newer than sink data 1
source.LUID_mtimes['1'] = '1'
sink.modified = ['1','5']
#make sink data 5 newer than source data 5
sink.LUID_mtimes['5'] = '1'
test.set_two_way_policy({"conflict":"skip","deleted":"skip"})
sync_and_check_result(
        name="2Way",
        description="modify both (conflict policy: skip)",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=3,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

#phase three: modify both (modify policy: ask)
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
sync_and_check_result(
        name="2Way",
        description="modify both (conflict policy: ask)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=3,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

#phase three: modify both (modify policy: replace)
test.set_two_way_policy({"conflict":"replace","deleted":"skip"})
sync_and_check_result(
        name="2Way",
        description="modify both (conflict policy: replace)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=3,
        sinkExpects=(1,0),
        sourceExpects=(1,0))

#phase four: test mod and delete (delete policy: skip)
test.set_two_way_policy({"conflict":"replace","deleted":"skip"})
reset_dataproviders(source, sink)
source.modified = ['3']
sink.deleted = ['3']
sync_and_check_result(
        name="2Way",
        description="mod+del (delete policy: skip)",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=3,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

#phase four: test mod and delete (delete policy: ask)
test.set_two_way_policy({"conflict":"skip","deleted":"ask"})
sync_and_check_result(
        name="2Way",
        description="mod+del (delete policy: ask)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=3,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

#phase four: test mod and delete (delete policy: replace)
test.set_two_way_policy({"conflict":"skip","deleted":"replace"})
sync_and_check_result(
        name="2Way",
        description="mod+del (delete policy: replace)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=2,
        sinkExpects=(0,0),
        sourceExpects=(0,1))

################################################################################
# ONE WAY SYNC WITH ONE SOURCE AND ONE SINK
################################################################################
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
sync_and_check_result(
        name="1Way",
        description="add data",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=5,
        sinkExpects=(5,0),
        sourceExpects=(0,0))

#phase two: mod data
reset_dataproviders(source, sink)
source.modified = ['1','2','3']
sync_and_check_result(
        name="1Way",
        description="modify data",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=5,
        sinkExpects=(3,0),
        sourceExpects=(0,0))

#phase three: delete data
reset_dataproviders(source, sink)
source.deleted = ['1','2','3']
test.set_two_way_policy({"conflict":"ask","deleted":"skip"})
sync_and_check_result(
        name="1Way",
        description="delete data (delete policy: skip)",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=5,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
sync_and_check_result(
        name="1Way",
        description="delete data (delete policy: ask)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=5,
        sinkExpects=(0,0),
        sourceExpects=(0,0))

test.set_two_way_policy({"conflict":"ask","deleted":"replace"})
sync_and_check_result(
        name="1Way",
        description="delete data (delete policy: replace)",
        test=test,
        expectedResult=(False,False,True),
        expectedMappings=2,
        sinkExpects=(0,3),
        sourceExpects=(0,0))

################################################################################
# SLOW SYNC
################################################################################
class TestShellGetAll(TestShell):
    def get_changes(self):
        raise NotImplementedError

source = TestShellGetAll(uid="X")
sink = TestShellGetAll(uid="Y")
sourceDpw = test.wrap_dataprovider(source)
sinkDpw = test.wrap_dataprovider(sink)
test.prepare(
        sourceDpw, 
        sinkDpw
        )
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})

#phase one: add data
reset_dataproviders(source, sink)
source.added = ['1','2','3']
sync_and_check_result(
        name="Slow",
        description="add data",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=3,
        sinkExpects=(3,0))

#phase one: add data
reset_dataproviders(source, sink)
source.added = ['1','2','3']
sync_and_check_result(
        name="Slow",
        description="no new data",
        test=test,
        expectedResult=(False,False,False),
        expectedMappings=3,
        sinkExpects=(0,0))

finished()
