import gtk
import gobject
import random
import logging
import conduit
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.Module as Module
from conduit.datatypes import DataType

import time

MODULES = {
	"TestSource" :          { "type": "dataprovider" },
	"TestSink" :            { "type": "dataprovider" },
	"TestTwoWay" :          { "type": "dataprovider" },
	"TestSinkFailRefresh" : { "type": "dataprovider" },
    "TestFactory" :         { "type": "dataprovider-factory" }
}

#Test datatype is a thin wrapper around an integer string in the form
#"xy" where x is supplied at construction time, and y is a random integer
#in the range 0-9. 
class TestDataType(DataType.DataType):
    def __init__(self, integerData):
        DataType.DataType.__init__(self,"text")
        self.UID = integerData
        
    def __str__(self):
        return "testData %s" % self.UID
    
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

    def get_UID(self):
        return str(self.UID)
            

class _TestBase:
    def __init__(self):
        #Through an error on the nth time through
        self.errorAfter = 999
        self.slow = False
        self.UID = Utils.random_string()
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


    NUM_DATA = 5    
    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSource.__init__(self)
        
    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return TestSource.NUM_DATA

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        if self.slow:
            time.sleep(2)
        data = TestDataType(index)
        logging.debug("TEST SOURCE: get() returned %s" % data)
        if index == self.errorAfter:
            raise Exceptions.SyncronizeError
        return data
		
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
        
    def put(self, data, overwrite, LUIDs=[]):
        DataProvider.DataSink.put(self, data, overwrite)
        if self.slow:
            time.sleep(1)    
        if self.count == self.errorAfter:
            raise Exceptions.SyncronizeError
        self.count += 1
        #the LUID of any test data passed in is the original 
        #data + the dp name
        if len(LUIDs) > 0:
            logging.debug("TEST SINK: put(): %s (known UID:%s)" % (data,len(LUIDs)>0))
        return data.get_UID()+self._name_

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

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.data = []
        #Assemble a random array of data
        for i in range(0, random.randint(1, TestTwoWay.NUM_DATA)):
            self.data.append(TestDataType(i))

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        num = len(self.data)
        logging.debug("TWO WAY: get_num_items() returned %s" % num)
        return num

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        data = self.data[index]
        logging.debug("TWO WAY: get() returned %s" % data)
        return data

    def put(self, data, overwrite, LUIDs=[]):
        DataProvider.TwoWay.put(self, data, overwrite, LUIDs)
        logging.debug("TWO WAY: put() %s" % data)

    def finish(self):
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
        
    def refresh(self):
        DataProvider.DataSink.refresh(self)
        raise Exceptions.RefreshError

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
        gobject.timeout_add(4000, self.make_one)
        gobject.timeout_add(7000, self.make_two)
        
    def make_one(self, *args):
        self.emit_added(
                klass=TestDynamicSource,
                initargs=("Foo",), 
                category=DataProvider.CATEGORY_TEST)
        return False

    def make_two(self, *args):
        self.emit_added(
                klass=TestDynamicSource,
                initargs=("Bar","Baz"), 
                category=DataProvider.CATEGORY_TEST)
        #run once
        return False
