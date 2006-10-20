import gtk
import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions

import time

MODULES = {
	"TestSource" : {
		"name": "Test Source",
		"description": "Prints Debug Messages",
		"type": "source",
		"category": "Test",
		"in_type": "text",
		"out_type": "text"
	},
	"TestSink" : {
		"name": "Test Sink",
		"description": "Prints Debug Messages",
		"type": "sink",
		"category": "Test",
		"in_type": "text",
		"out_type": "text"
	},
	"TestTwoWay" : {
		"name": "Two Way",
		"description": "Prints Debug Messages",
		"type": "source",
		"category": "Test",
		"in_type": "text",
		"out_type": "text"
	},
	"TestSinkFailRefresh" : {
		"name": "Test Refresh Sink",
		"description": "Fails Refresh",
		"type": "sink",
		"category": "Test",
		"in_type": "text",
		"out_type": "text"
	},

}

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
        
    def refresh(self):
        #Print out values of the instance vars
        import textwrap
        logging.debug(  textwrap.dedent("""
                        Instance Variables:
                        errorAfter\t%s
                        slow\t\t%s
                        aString\t\t%s
                        aInt\t\t%s
                        aBool\t\t%s
                        aList\t\t%s
                        """) % (
                        self.errorAfter,
                        self.slow,
                        self.aString,
                        self.aInt,
                        self.aBool,
                        self.aList,
                        ))
        del textwrap

        
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
    def __init__(self):
        TestBase.__init__(self)
        DataProvider.DataSource.__init__(self, "Test Source", "Prints Debug Messages")
        
    def get(self):
        for i in range(0,5):
            if self.slow:
                time.sleep(2)
            string = "Test #%s" % i
            logging.debug("TEST SOURCE: get() returned %s" % string)
            if i == self.errorAfter:
                raise Exceptions.SyncronizeError
            yield string
		
class TestSink(TestBase, DataProvider.DataSink):
    def __init__(self):
        TestBase.__init__(self)
        DataProvider.DataSink.__init__(self, "Test Sink", "Prints Debug Messages")
        self.count = 0
        
    def put(self, data, dataOnTopOf=None):
        if self.slow:
            time.sleep(1)    
        if self.count == self.errorAfter:
            raise Exceptions.SyncronizeError
        self.count += 1
        logging.debug("TEST SINK: put(): %s" % data)

class TestTwoWay(DataProvider.DataSink, DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataProviderBase.__init__(self, "Two Way", "Prints Debug Messages")

    def initialize(self):
        return False

class TestSinkFailRefresh(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, "Test Refresh Sink", "Fails Refresh")
        
    def initialize(self):
        return False

    def refresh(self):
        raise Exceptions.RefreshError
