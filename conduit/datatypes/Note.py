import conduit
from conduit import log,logd,logw
from conduit.datatypes import DataType

class Note(DataType.DataType):
    """
    Represents a Note
    """
    def __init__(self, **kwargs):
        """
        Note constructor.
        Compulsory kwargs
          - title: The title of the note

        Optional kwargs
          - contents: The raw note contents
          - modified: Unix timestamp modified time
          - raw: Raw note XML. This should probbably be removed and put into
          - a dedicated TomboyNote datatype at some point.
        """
        DataType.DataType.__init__(self,"note")
        self.title = kwargs["title"]
        self.contents = kwargs.get("contents","")
        self.raw = kwargs.get("raw", "")

        self.set_mtime(kwargs.get("mtime", None))
        self.set_UID(self.title)

    def compare(self, B):
        """
        Compares two notes: Approach
          1. If the notes have valid mtimes then use that as an age comparison.
          2. If they have raw xml then use that as an equality comparison
          3. Otherwise do an equality comparison on title & contents
          4. Otherwise Unknown
        """
        #Look at the modification times
        meTime = self.get_mtime()
        bTime = B.get_mtime()
        logd("MTIME: %s with MTIME: %s" % (meTime, bTime))
        if meTime != None and bTime != None:
            logd("Comparing %s (MTIME: %s) with %s (MTIME: %s)" % (self.title, meTime, B.title, bTime))
            if meTime == bTime:
                return conduit.datatypes.COMPARISON_EQUAL
            #newer than B?
            elif meTime > bTime:
                return conduit.datatypes.COMPARISON_NEWER
            #older than B?
            elif meTime < bTime:
                return conduit.datatypes.COMPARISON_OLDER
            else:
                return conduit.datatypes.COMPARISON_UNKNOWN

        #look at raw xml
        elif self.raw != "" and B.raw != "":
            logd("Comparing via XML")
            if self.raw == B.raw:
                return conduit.datatypes.COMPARISON_EQUAL
            else:
                return conduit.datatypes.COMPARISON_UNKNOWN

        #else look at text (title + content)
        elif self.get_note_string() == B.get_note_string():
            return conduit.datatypes.COMPARISON_EQUAL

        else:
            return conduit.datatypes.COMPARISON_UNKNOWN

    def set_from_note_string(self, string):
        raise NotImplementedError

    def get_note_string(self):
        return ("Title: %s\n%s\n(Modified: %s)" % (self.title, self.contents, self.get_mtime()))
        
    def __str__(self):
        return self.title
        


