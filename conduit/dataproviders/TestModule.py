import gtk
import logging
import conduit
import conduit.DataProvider as DataProvider

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
        
    def initialize(self):
        return False

    def configure(self, window):
        def set(param):
            self.errorAfter = int(param)
        items = [
                    {
                    "Name" : "Error At:",
                    "Widget" : gtk.Entry,
                    "Callback" : set,
                    "InitialValue" : self.errorAfter
                    }                    
                ]
        dialog = DataProvider.DataProviderSimpleConfigurator(window, self.name, items)
        dialog.run()

class TestSource(TestBase, DataProvider.DataSource):
    def __init__(self):
        TestBase.__init__(self)
        DataProvider.DataSource.__init__(self, "Test Source", "Prints Debug Messages")
        
    def get(self):
        for i in range(0,5):
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
        if self.count == self.errorAfter:
            raise Exceptions.SyncronizeError
        self.count += 1
        logging.debug("TEST SINK: put(): %s" % data)
