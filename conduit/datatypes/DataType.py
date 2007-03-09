import conduit.datatypes

CHANGE_UNMODIFIED = 0
CHANGE_ADDED = 1
CHANGE_MODIFIED = 2
CHANGE_DELETED = 3

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
        self.change_type = CHANGE_UNMODIFIED

        self._original_URI = None
        self._mtime = None
        self._UID = None

    def compare(self, B):
        """
        Comparison function to be overridden by datatypes who support two
        way synchronisation. 
        
        This funcion should compare self with B. All answers 
        are from the perspective of the me (the instance)
        
         - C{conduit.datatypes.NEWER} This means the I am newer than B
         - C{conduit.datatypes.EQUAL} This means the we are equal
         - L{conduit.datatypes.OLDER} This means the I am older than B
         - L{conduit.datatypes.UNKNOWN} This means we were unable to determine
           which was newer than the other so its up to the user to decide
        
        """
        return conduit.datatypes.UNKNOWN

    def get_hash(self):
        return ""

    def get_UID(self):
        """
        Returns the UID of the datatype
        """
        return self._UID

    def set_UID(self, UID):
        """
        Sets the UID of the datatype
        @type UID: C{string}
        """
        self._UID = UID

    def set_mtime(self, mtime):
        """
        Sets the modification time of the datatype.
        @type mtime: C{datetime.datetime}
        """
        self._mtime = mtime

    def get_mtime(self):
        """
        @returns: The file modification time (or None) as a python datetime object
        @rtype: C{datetime.datetime}
        """
        return self._mtime

    def get_open_URI(self):
        """
        @returns: The URI that can be opened through gnome-open (or None)
        """
        return self._original_URI

    def set_open_URI(self, URI):
        """
        Saves the URI that can be opened through gnome-open
        """
        self._original_URI = URI

    def get_snippet(self):
        """
        Returns a small representation of the data that may be shown to the
        user. Derived types may override this function.
        """
        s = ""
        uri = self.get_open_URI()
        mtime = self.get_mtime()

        if uri != None:
            s += "%s" % uri
        if mtime != None:
            s += " (%s)" % mtime.strftime("%c")

        if s == "":
            s += "%s" % str(self)
        else:
            s += "\n%s" % str(self)

        return s


