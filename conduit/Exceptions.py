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
    def __init__(self, fromType, toType):
        self.fromType = fromType
        self.toType = toType
        Exception.__init__(self,
            "Could not convert: %s -> %s" % (self.fromType, self.toType)
            )

class ConversionDoesntExistError(Exception):
    """
    Thrown when the typeconverter tries a conversion that does not exist
    """
    def __init__(self, fromType, toType):
        self.fromType = fromType
        self.toType = toType
        Exception.__init__(self,
            "No conversion exists: %s -> %s" % (self.fromType, self.toType)
            )

class RefreshError(Exception):
    """
    Exception thrown upon failure to refresh conduit
    """
    pass

class NotSupportedError(Exception):
    """
    Exception thrown when a dataprovider cannot be loaded
    """
    pass    
    
class SyncronizeError(Exception):
    """
    Non-fatal, i.e. dont stop the whole sync process, just ignore this 
    one particular attempt to get() a resource as failed
    """
    pass
    
class SyncronizeFatalError(Exception):
    """
    Fatal error returned from sync. Do not attempt again
    """
    pass
    
class SynchronizeConflictError(Exception):
    """
    Raised in the put() method when the input data conflicts with data 
    already present and user intervention is needed to resolve
    """
    def __init__(self, comparison, fromData, toData):
        self.comparison = comparison
        self.fromData = fromData
        self.toData = toData
        Exception.__init__(self,
            "Comparison=%s (From: %s, To:%s)" % (self.comparison, self.fromData, self.toData)
            )

class StopSync(Exception):
    """
    Raised by the syncworker to tell the syncmanager to stop
    """
    def __init__(self, step=0):    
        self.step = step
        Exception.__init__(self,
            "Synchronization aborted at step %s" % self.step
            )

