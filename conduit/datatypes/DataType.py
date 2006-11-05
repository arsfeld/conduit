import conduit.datatypes

class DataType:
    """
    Base DataType which represents any thing 
    which can be synchronized between two DataProviders

    @ivar type_name: The name of the type
    @type type_name: C{string}
    @ivar URI: A URI which uniquely represents the location of the datatype. 
    @type URI: C{string}
    @ivar UID: A Unique identifier for this type. This is particuarly 
    neccessary on types that are used in two-way sync.
    @type UID: C{string}
    """
    def __init__(self,type_name):
        self.type_name = type_name
        self.URI = None
        self.UID = None

    def compare(self, A, B):
        """
        Comparison function to be overridden by datatypes who support two
        way synchronisation. 
        
        This funcion should compare A with B. All answers 
        are from the perspective of A. The function should return
        
         - C{conduit.datatypes.NEWER} This means the A is newer than B
         - C{conduit.datatypes.EQUAL} This means the items are equal
         - L{conduit.datatypes.OLDER} This means the A is older than B
         - L{conduit.datatypes.UNKNOWN} This means we were unable to determine
           which was newer than the other so its up to the user to decide
        
        """
        return conduit.datatypes.EQUAL

    def set_UID(self, UID):
        """
        Sets the UID for the data
        """
        self.UID = UID

    def get_UID(self, UID):
        """
        Gets the UID for this data
        """
        return self.UID
