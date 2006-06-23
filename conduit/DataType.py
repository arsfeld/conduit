import gtk
import gobject

#Constants used for comparison
EQUAL = 0
NEWER = 1
OLDER = 2
ERROR = 3

class DataType(gobject.GObject):
    """Base DataType which represents any thing 
    which can be synchronized between two DataProviders
    """
    
    def __init__(self, name=None, description=None):
        gobject.GObject.__init__(self)

        self.name = name
        self.description = description
        
    def initialize(self):
        print "not implemented"   
        
    def synchronize(self):
        return EQUAL
