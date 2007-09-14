"""
Exceptions used to convey information during the sync process

Copyright: John Stowers, 2006
License: GPLv2
"""

class ConversionError(Exception):
    """
    Exception thrown by TypeConverter when it could not convert stuff due to an
    error in the conversion function
    """
    def __init__(self, fromType, toType, extraMsg=None):
        """
        Store some extra information so we can provide a more helpful
        error message
        
        @type fromType: C{str}
        @type toType: C{str}
        @param extraMsg: An additional, probbably conversion specific message
        to be included in the error
        @type extraMsg: C{str}
        """
        self.fromType = fromType
        self.toType = toType
        self.msg = extraMsg        
        
    def __str__(self):
        return "ConversionError: Could not convert %s -> %s\nExtra Info: %s" % (self.fromType, self.toType, self.msg)

class ConversionDoesntExistError(Exception):
    """
    Thrown when the typeconverter tries a conversion that does not exist
    """
    def __init__(self, fromType, toType):
        self.fromType = fromType
        self.toType = toType
        
    def __str__(self):
        return "ConversionDoesntExistError: Could not convert %s -> %s" % (self.fromType, self.toType)

class RefreshError(Exception):
    """
    Exception thrown upon failure to refresh conduit
    """
    pass
    
class SyncronizeError(Exception):
    """
    Non-fatal, i.e. dont stop the whole sync process, just ignore this 
    one particular attempt to get() a resource as failed
    """
    def __init__(self, extraMsg=None):
        self.msg = extraMsg
        
    def __str__(self):
        return "Non Fatal Synchronize Error\nExtra Info: %s" % (self.msg)
    
class SyncronizeFatalError(Exception):
    """
    Fatal error returned from sync. Do not attempt again
    """
    def __init__(self, extraMsg=None):
        self.msg = extraMsg
        
    def __str__(self):
        return "Fatal Synchronize Error\nExtra Info: %s" % (self.msg)
    
class SynchronizeConflictError(Exception):
    """
    Raised in the put() method when the input data conflicts with data 
    already present and user intervention is needed to resolve
    """
    def __init__(self, comparison, fromData, toData):
        """
        Store the info required to resume this sync later
        """
        self.comparison = comparison
        self.fromData = fromData
        self.toData = toData

    def __str__(self):
        return "SynchronizeConflictError: Comparison=%s (From: %s, To:%s)" % (self.comparison, self.fromData, self.toData)

        
class StopSync(Exception):
    """
    Raised by the syncworker to tell the manager to pack his bags and
    go home
    """
    def __init__(self, step=0):    
        """
        Optionally we can specify the step at which the sync
        was aborted to make a nicer error message
        """
        self.step = step
        
    def __str__(self):
        return "StopSync: Sync aborted at step %s" % self.step
        
            
    
