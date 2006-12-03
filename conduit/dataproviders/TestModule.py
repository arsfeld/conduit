import gtk
import random
import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
from conduit.datatypes import DataType

import time

MODULES = {
	"TestSource" : {
		"name": "Test Source",
		"description": "Prints Debug Messages",
		"type": "source",
		"category": DataProvider.CATEGORY_TEST,
		"in_type": "text",
		"out_type": "text"
	},
	"TestSink" : {
		"name": "Test Sink",
		"description": "Prints Debug Messages",
		"type": "sink",
		"category": DataProvider.CATEGORY_TEST,
		"in_type": "text",
		"out_type": "text"
	},
	"TestTwoWay" : {
		"name": "Two Way",
		"description": "Prints Debug Messages",
		"type": "source",
		"category": DataProvider.CATEGORY_TEST,
		"in_type": "text",
		"out_type": "text"
	},
	"TestSinkFailRefresh" : {
		"name": "Test Refresh Sink",
		"description": "Fails Refresh",
		"type": "sink",
		"category": DataProvider.CATEGORY_TEST,
		"in_type": "text",
		"out_type": "text"
	},

}

#Test datatype is a thin wrapper around an integer string in the form
#"xy" where x is supplied at construction time, and y is a random integer
#in the range 0-9. 
class TestDataType(DataType.DataType):
    def __init__(self, integerData):
        DataType.DataType.__init__(self,"text")
        #In this case the UID is the data but that is not the case
        #for more complex datatypes
        self.UID = 10*integerData + random.randint(1,4)
        
    def __str__(self):
        return "testData %s" % self.UID
    
    #The strings are numerically compared. If A < B then it is older
    #If A is larger than B then it is newer.
    def compare(self, A, B):
        a = int(A.UID)
        b = int(B.UID)
        if a < b:
            return conduit.datatypes.OLDER
        elif a > b:
            return conduit.datatypes.NEWER
        elif a == b:
            return conduit.datatypes.EQUAL
        else:
            return conduit.datatypes.UNKNOWN
            

class TestBase:
    def __init__(self):
        #Through an error on the nth time through
        self.errorAfter = 999
        self.slow = False
        #Variables to test the config fuctions
        self.aString = ""
        self.aInt = 0
        self.aBool = False
        self.aList = []
        
    def initialize(self):
        return True

    def configure(self, window):
        def setError(param):
            self.errorAfter = int(param)
        def setSlow(param):
            self.slow = bool(param)            
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
                    }               
                ]
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        dialog.run()
        
    def get_configuration(self):
        return {
            "errorAfter" : self.errorAfter,
            "slow" : self.slow,
            "aString" : "im a string",
            "aInt" : 5,
            "aBool" : True,
            "aList" : ["ListItem1", "ListItem2"]
            }

class TestSource(TestBase, DataProvider.DataSource):
    NUM_DATA = 5    
    def __init__(self):
        TestBase.__init__(self)
        DataProvider.DataSource.__init__(self, "Test Source", "Prints Debug Messages", "emblem-system")
        
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
		
class TestSink(TestBase, DataProvider.DataSink):
    def __init__(self):
        TestBase.__init__(self)
        DataProvider.DataSink.__init__(self, "Test Sink", "Prints Debug Messages", "emblem-system")
        self.count = 0
        
    def put(self, data, dataOnTopOf=None):
        DataProvider.DataSink.put(self, data, dataOnTopOf)
        if self.slow:
            time.sleep(1)    
        if self.count == self.errorAfter:
            raise Exceptions.SyncronizeError
        self.count += 1
        logging.debug("TEST SINK: put(): %s" % data)

class TestTwoWay(TestSink, TestSource):
    def __init__(self):
        DataProvider.DataProviderBase.__init__(self, "Two Way", "Prints Debug Messages", "emblem-system")

    def initialize(self):
        return True

class TestSinkFailRefresh(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, "Test Refresh Sink", "Fails Refresh")
        
    def initialize(self):
        return True

    def refresh(self):
        DataProvider.DataSink.refresh(self)
        raise Exceptions.RefreshError
