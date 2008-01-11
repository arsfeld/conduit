"""
Utilty functions shared between the xml-rpc client and server

Copyright: John Stowers, 2006
License: GPLv2
"""

import xmlrpclib
import conduit.Exceptions as Exceptions

XML_RPC_EASY_EXCEPTIONS = (
    "RefreshError",
    "SyncronizeError",
    "SyncronizeFatalError",
    "StopSync"
    )
    
XML_RPC_EASY_DATAPROVIDER_METHODS = (
    "refresh",
    )

def marshal_fault_to_exception(fault, **kwargs):
    if fault.faultCode in XML_RPC_EASY_EXCEPTIONS:
        klass = getattr(Exceptions,fault.faultCode)
        #exception.message = fault.faultString
        raise klass(fault.faultString)
    elif fault.faultCode == "SynchronizeConflictError":
        fromData = kwargs['server'].get(kwargs['fromDataLUID'])
        toData = kwargs['toData']
        raise Exceptions.SynchronizeConflictError(fault.faultString, fromData, toData)
    else:
        raise Exception("Unknown xmlrpc.Fault: %s:%s" % (fault.faultCode,fault.faultString))

def marshal_exception_to_fault(exception):
    klassName = exception.__class__.__name__
    if klassName in XML_RPC_EASY_EXCEPTIONS:
        #exception.message = fault.faultString
        return xmlrpclib.Fault(klassName, exception.message)
    elif fault.faultCode == "SynchronizeConflictError":
        #only put the comparison in the fault, getting the other data 
        #requires subsequent xmlrpc calls
        return xmlrpclib.Fault("SynchronizeConflictError", exception.comparison)    
    else:
        return xmlrpclib.Fault("Unknown",exception.message)


