#common sets up the conduit environment
from common import *

import conduit
from conduit.datatypes import DataType
from conduit.dataproviders.DataProvider import TwoWay

import datetime

FOO_MTIME = datetime.datetime(1983,8,16)
BAR_MTIME = datetime.datetime(2007,2,23)
DB_DEBUG = True

class _DataType(DataType.DataType):
    def __init__(self, data, **kwargs):
        DataType.DataType.__init__(self)
        self.data = data                
    def get_hash(self):
        return hash( self.data )
                
class _TwoWay(TwoWay):
    _module_type_ = "twoway"
    def __init__(self, *args):
        TwoWay.__init__(self)
        
    def _get_data(self, LUID):
        dat = self.data_klass(LUID)
        dat.set_mtime(self.mtime)
        dat.set_UID(LUID)
        return dat
        
    def initialize(self):
        return True

    def get_all(self):
        TwoWay.get_all(self)
        return self.data

    def get(self, LUID):
        return self._get_data(LUID)

    def put(self, data, overwrite, LUID=None):
        TwoWay.put(self, data, overwrite, LUID)
        self.data.append(data.data)
        f = self._get_data(data.data)
        return f.get_rid()
        
    def get_UID(self):
        return ""
        
class FooDataType(_DataType):
    _name_ = "foo"
        
class FooTwoWay(_TwoWay):
    _in_type_ = "foo"
    _out_type_ = "foo"

    def __init__(self, *args):
        _TwoWay.__init__(self)
        self.data = ['A']
        self.mtime = FOO_MTIME
        self.data_klass = FooDataType

class BarDataType(_DataType):
    _name_ = "bar"
        
class BarTwoWay(_TwoWay):
    _in_type_ = "bar"
    _out_type_ = "bar"

    def __init__(self, *args):
        _TwoWay.__init__(self)
        self.data = ['M']
        self.mtime = BAR_MTIME
        self.data_klass = BarDataType

class FooBarConverter(object):
    def __init__(self):
        self.conversions =  {
                "foo,bar"           : self.foo_to_bar,
                "bar,foo"           : self.bar_to_foo
        }
    def foo_to_bar(self, data, **kwargs):
        return data
        
    def bar_to_foo(self, data, **kwargs):
        return data

#Setup the test environment
test = SimpleSyncTest()

#instantiate modules and add with wrappers
source = FooTwoWay()
sink = BarTwoWay()
conv = FooBarConverter()

convDpw = test.wrap_dataprovider(conv)
sourceDpw = test.wrap_dataprovider(source)
sinkDpw = test.wrap_dataprovider(sink)

test.type_converter._add_converter(convDpw)
test.prepare(
        sourceDpw, 
        sinkDpw
        )
test.set_two_way_sync(True)

#Check both source and sink get data
so,sk = test.sync(debug=DB_DEBUG)
ok("Sync'd data", so == 2 and sk == 2)

#Modify t
sink.mtime=datetime.datetime(2007,2,24)
test.sync(debug=DB_DEBUG)

maps = conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(
                            sourceUID=sink.get_UID(),
                            sinkUID=source.get_UID()
                            )

test.sync(debug=DB_DEBUG)

finished()
