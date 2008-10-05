import logging
log = logging.getLogger("datatypes.DataType")

import conduit.datatypes

CHANGE_UNMODIFIED = 0
CHANGE_ADDED = 1
CHANGE_MODIFIED = 2
CHANGE_DELETED = 3

class DataType(object):
    """
    Base DataType which represents any thing 
    which can be synchronized between two DataProviders

    @cvar _name_: The name of the type
    @type _name_: C{string}
    @ivar URI: A URI which uniquely represents the location of the datatype. 
    @type URI: C{string}
    @ivar UID: A Unique identifier for this type. This is particuarly 
    neccessary on types that are used in two-way sync.
    @type UID: C{string}
    """

    _name_ = ""

    def __init__(self):
        self.change_type = CHANGE_UNMODIFIED

        self._original_URI = None
        self._mtime = None
        self._UID = None
        self._tags = ()

    def get_type(self):
        """
        @returns: The type (name) of this datatype
        @rtype: C{string}
        """
        return self._name_

    def compare(self, B, sinkUID=None):
        """
        Comparison function to be overridden by datatypes who support two
        way synchronisation. 
        
        This funcion should compare self with B. All answers 
        are from the perspective of the me (the instance)
        
         - C{conduit.datatypes.COMPARISON_NEWER} This means the I am newer than B
         - C{conduit.datatypes.COMPARISON_EQUAL} This means the we are equal
         - L{conduit.datatypes.COMPARISON_OLDER} This means the I am older than B
         - L{conduit.datatypes.COMPARISON_UNKNOWN} This means we were unable to determine
           which was newer than the other so its up to the user to decide        
        """
        log.debug("COMPARE: %s <----> %s " % (self.get_UID(), B.get_UID()))

        m = None
        if sinkUID:
            m = conduit.GLOBALS.mappingDB.get_mapping_from_objects(self.get_UID(), B.get_UID(), sinkUID)

        if self.get_rid() == B.get_rid():
            return conduit.datatypes.COMPARISON_EQUAL

        mtime1 = self.get_mtime()
        mtime2 = B.get_mtime()

        # resolve conflicts with hashes if only one side has changed and mtimes are not useful
        if (mtime1 == None or mtime2 == None) and m and m.get_sink_rid().get_hash() == B.get_hash():
            return conduit.datatypes.COMPARISON_NEWER
        elif mtime1 == None or mtime2 == None:
            return conduit.datatypes.COMPARISON_UNKNOWN

        if mtime1 > mtime2:
            return conduit.datatypes.COMPARISON_NEWER
        else:
            return conduit.datatypes.COMPARISON_OLDER

    def get_hash(self):
        raise NotImplementedError

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

    def get_tags(self):
        """
        @returns: the current list of tags
        """
        return self._tags

    def set_tags(self, tags):
        """
        Sets the tags of the datatype
        """
        self._tags = tags

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

    def get_rid(self):
        """
        @returns: The record identifier (Rid) for this data
        """
        log.debug("Getting Rid for %s" % self.get_UID())
        rid = conduit.datatypes.Rid(
                        uid=self.get_UID(), 
                        mtime=self.get_mtime(), 
                        hash=self.get_hash()
                        )
        return rid

    def __getstate__(self):
        """
        Store the object state in a dict for pickling
        """
        data = {}
        data['mtime'] = self.get_mtime()
        data['uid'] = self.get_UID()
        data['open_uri'] = self.get_open_URI()
        data['tags'] = self.get_tags()
        return data

    def __setstate__(self, data):
        """
        Set object state from dict (after unpickling)
        """
        self.set_mtime(data['mtime'])
        self.set_UID(data['uid'])
        self.set_open_URI(data['open_uri'])
        self.set_tags(data['tags'])
        
