import gtk
import gobject
import random
import datetime

import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.Module as Module
from conduit.datatypes import DataType

import time

MODULES = {
    "TestSource" :          { "type": "dataprovider" },
    "TestSink" :            { "type": "dataprovider" },
    "TestConflict" :        { "type": "dataprovider" },
    "TestChangeType" :      { "type": "dataprovider" },
    "TestTwoWay" :          { "type": "dataprovider" },
    "TestSinkFailRefresh" : { "type": "dataprovider" },
    "TestFactory" :         { "type": "dataprovider-factory" },
#    "TestFactoryRemoval" :  { "type": "dataprovider-factory" },
    "CheeseConverter" :     { "type": "converter" }
}

#Test datatype is a thin wrapper around an integer string in the form
#"xy" where x is supplied at construction time, and y is a random integer
#in the range 0-9. 
class TestDataType(DataType.DataType):
    def __init__(self, integerData):
        DataType.DataType.__init__(self,"text")
        self.UID = integerData

        self.set_open_URI("file:///home/")
        self.set_UID(str(self.UID))
        self.set_mtime(datetime.datetime(2003,8,16))
        
    def __str__(self):
        return "testData %s" % self.UID

    def get_snippet(self):
        return str(self) + "\nI am a piece of test data"
     
    #The strings are numerically compared. If A < B then it is older
    #If A is larger than B then it is newer.
    def compare(self, A, B):
        a = int(A.UID)
        b = int(B.UID)
        if a < b:
            return conduit.datatypes.COMPARISON_OLDER
        elif a > b:
            return conduit.datatypes.COMPARISON_NEWER
        elif a == b:
            return conduit.datatypes.COMPARISON_EQUAL
        else:
            return conduit.datatypes.COMPARISON_UNKNOWN

class _TestBase:
    def __init__(self):
        #Through an error on the nth time through
        self.errorAfter = 999
        self.slow = False
        self.UID = Utils.random_string()
        self.numData = 5
        #Variables to test the config fuctions
        self.aString = ""
        self.aInt = 0
        self.aBool = False
        self.aList = []
        self.count = 0
        
    def initialize(self):
        return True

    def configure(self, window):
        def setError(param):
            self.errorAfter = int(param)
        def setSlow(param):
            self.slow = bool(param)
        def setUID(param):
            self.UID = str(param)        
        def setNumData(param):
            self.numData = int(param)
        items = [
                    {
                    "Name" : "Error At:",
                    "Widget" : gtk.Entry,
                    "Callback" : setError,
                    "InitialValue" : self.errorAfter
                    },
                    {
                    "Name" : "Take a Long Time?",
                    "Widget" : gtk.CheckButton,
                    "Callback" : setSlow,
                    "InitialValue" : self.slow
                    },
                    {
                    "Name" : "UID",
                    "Widget" : gtk.Entry,
                    "Callback" : setUID,
                    "InitialValue" : self.UID
                    },
                    {
                    "Name" : "Num Data",
                    "Widget" : gtk.Entry,
                    "Callback" : setNumData,
                    "InitialValue" : self.numData
                    } 
                ]
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self._name_, items)
        dialog.run()

    def get_UID(self):
        return self.UID
        
    def get_configuration(self):
        return {
            "errorAfter" : self.errorAfter,
            "slow" : self.slow,
            "UID" : self.UID,
            "aString" : "im a string",
            "aInt" : 5,
            "aBool" : True,
            "aList" : ["ListItem1", "ListItem2"]
            }

class TestSource(_TestBase, DataProvider.DataSource):

    _name_ = "Test Source"
    _description_ = "Prints Debug Messages"
    _category_ = DataProvider.CATEGORY_TEST
    _module_type_ = "source"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSource.__init__(self)
        
        #signal we have new data in a few seconds
        gobject.timeout_add(3000, self._emit_change)

    def _emit_change(self):
        self.emit_change_detected()
        return False
       
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        return range(0,self.numData)

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        if self.slow:
            time.sleep(2)
        data = TestDataType(index)
        logd("TEST SOURCE: get() returned %s" % data)
        if index == self.errorAfter:
            raise Exceptions.SyncronizeError
        return data

    def add(self, LUID):
        return True
		
class TestSink(_TestBase, DataProvider.DataSink):

    _name_ = "Test Sink"
    _description_ = "Prints Debug Messages"
    _category_ = DataProvider.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSink.__init__(self)
        
    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        if self.slow:
            time.sleep(1)    
        if self.count == self.errorAfter:
            raise Exceptions.SyncronizeError
        self.count += 1
        logd("TEST SINK: put(): %s (known UID:%s)" % (data,LUID))
        LUID=data.get_UID()+self._name_
        return LUID

class TestTwoWay(_TestBase, DataProvider.TwoWay):

    _name_ = "Test Two Way"
    _description_ = "Prints Debug Messages"
    _category_ = DataProvider.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    NUM_DATA = 10
    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.TwoWay.__init__(self)
        self.data = None
        self.numData = 10

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.data = []
        #Assemble a random array of data
        for i in range(0, random.randint(1, self.numData)):
            self.data.append(TestDataType(i))

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.data

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return LUID

    def put(self, data, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        LUID=data.get_UID()+self._name_
        return LUID

    def finish(self): 
        DataProvider.TwoWay.finish(self)
        self.data = None

class TestSinkFailRefresh(_TestBase, DataProvider.DataSink):

    _name_ = "Test Fail Refresh"
    _description_ = "Test Sink Fails Refresh"
    _category_ = DataProvider.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSink.__init__(self)
        self.need_configuration(True)
        
    def refresh(self):
        DataProvider.DataSink.refresh(self)
        raise Exceptions.RefreshError

    def configure(self, window):
        self.set_configured(True)

class TestConflict(DataProvider.DataSink):

    _name_ = "Test Conflict"
    _description_ = "Test Sink Conflict"
    _category_ = DataProvider.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)

    def refresh(self):
        DataProvider.DataSink.refresh(self)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        if not overwrite:
            raise Exceptions.SynchronizeConflictError(conduit.datatypes.COMPARISON_UNKNOWN, data, TestDataType(0))
        LUID=data.get_UID()+self._name_
        return LUID

    def get_UID(self):
        return Utils.random_string()

class TestChangeType(DataProvider.DataSink):

    _name_ = "Test Change Type"
    _description_ = "Test Sink ChangeType"
    _category_ = DataProvider.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "text"
    _out_type_ = ""
    _icon_ = "emblem-system"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.use_cheese = False

    def configure(self, window):
        def setCheese(param):
            self.use_cheese = bool(param)
        items = [
                    {
                    "Name" : "Convert Test Data to Cheese?",
                    "Widget" : gtk.CheckButton,
                    "Callback" : setCheese,
                    "InitialValue" : self.use_cheese
                    }
                ]
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self._name_, items)
        dialog.run()

    def refresh(self):
        DataProvider.DataSink.refresh(self)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        return None

    def get_UID(self):
        return Utils.random_string()

    def get_in_type(self):
        if self.use_cheese:
            return "cheese"
        else:
            return self._in_type_

class CheeseConverter:
    def __init__(self):
        self.conversions =  {"text,cheese"   : self.convert}
                            
    def convert(self, text):
        return TestDataType(0)


class TestDynamicSource(_TestBase, DataProvider.DataSource):
    _name_ = "Test Dynamic Source"
    _description_ = "Prints Debug Messages"
    _module_type_ = "source"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSource.__init__(self)

class TestFactory(Module.DataProviderFactory):
    def __init__(self, **kwargs):
        Module.DataProviderFactory.__init__(self, **kwargs)

        #callback the GUI in 5 seconds to add a new dataprovider
        gobject.timeout_add(3000, self.make_one)
        gobject.timeout_add(5000, self.make_two)
        gobject.timeout_add(7000, self.remove_one)
        
    def make_one(self, *args):
        self.key1 = self.emit_added(
                            klass=TestDynamicSource,
                            initargs=("Foo",), 
                            category=DataProvider.CATEGORY_TEST)
        #run once
        return False

    def make_two(self, *args):
        self.key2 = self.emit_added(
                             klass=TestDynamicSource,
                             initargs=("Bar","Baz"), 
                             category=DataProvider.CATEGORY_TEST)
        #run once
        return False

    def remove_one(self, *args):
        self.emit_removed(self.key1)
        return False

class TestFactoryRemoval(Module.DataProviderFactory):
    """
    Repeatedly add/remove a DP/Category to stress test framework
    """
    def __init__(self, **kwargs):
        Module.DataProviderFactory.__init__(self, **kwargs)
        gobject.timeout_add(5000, self.added)
        self.count = 200
        self.stats = None

        self.cat = DataProvider.DataProviderCategory(
                    "TestHotplug",
                    "emblem-system",
                    "/test/")

    def added(self):
        if self.stats == None:
            self.stats = conduit.memstats()

        self.key = self.emit_added(
                           klass=TestDynamicSource,
                           initargs=("Bar","Bazzer"),
                           category=self.cat)

        gobject.timeout_add(500, self.removed)
        return False

    def removed(self):
        self.emit_removed(self.key)
        if self.count > 0:
            gobject.timeout_add(500, self.added)
            self.count -= 1
        else:
            conduit.memstats(self.stats)
        return False


