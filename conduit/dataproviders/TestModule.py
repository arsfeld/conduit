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
}

class TestBase:
    def __init__(self):
        #Through an error on the nth time through
        self.errorAfter = 999
        self.slow = False
        
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
            "slow" : self.slow
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
        
    def put(self, data):
        if self.slow:
            time.sleep(1)    
        if self.count == self.errorAfter:
            raise Exceptions.SyncronizeError
        self.count += 1
        logging.debug("TEST SINK: put(): %s" % data)
