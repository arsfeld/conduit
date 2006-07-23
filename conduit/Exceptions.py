class ConversionError(Exception):
    """
    Exception thrown by TypeConverter when it could not convert stuff
    """
    def __init__(self, fromType, toType, extraMsg=None):
        self.fromType = fromType
        self.toType = toType
        self.msg = extraMsg        
        
    def __str__(self):
        if self.msg is None:
            return "Could not convert %s -> %s" % (self.fromType, self.toType)
        else:
            return "Could not convert %s -> %s\nExtra info:\n%s" % (self.fromType, self.toType, self.msg)

class InitializeError(Exception):
    """
    Exception thrown upon failure to intialize conduit
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
    
    @todo: Should accept the from_data, the to_data, and the datasink to 
    allow this to be continued later
    """
    def __init__(self,fromData, toData, datasink):
        self.fromData = fromData
        self.toData = toData
        self.datasink = datasink

    def __str__(self):
        return "Sync Conflict (From: %s, To:%s, Data:%s" % (self.fromData, self.toData, self.datasink)

        
class StopSync(Exception):
    """
    Raised by the syncworker to tell the manager to pack his bags and
    go home
    """
    def __init__(self, step=0):    
        self.step = step
        
    def __str__(self):
        return "Sync aborted at step %s" % self.step
        
            
    
