import gtk
import gobject

#Constants used for comparison
EQUAL = 0
NEWER = 1
OLDER = 2
ERROR = 3

class DataType(gobject.GObject):
    """
    Base DataType which represents any thing 
    which can be synchronized between two DataProviders
    """
    
    def __init__(self, name=None, description=None, type_name=None):
        gobject.GObject.__init__(self)

        self.name = name
        self.description = description
        self.type_name = type_name
        self.the_type = None
        
    def initialize(self):
        """
        Initialize
        """
        print "not implemented"   
        
    def compare(self, from_type, to_type):
        """
        Synchronize
        """
        return EQUAL
