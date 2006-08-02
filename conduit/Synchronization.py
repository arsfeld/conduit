"""
Holds class used for the actual synchronisation phase

Copyright: John Stowers, 2006
License: GPLv2
"""

import traceback
import threading

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions

class SyncManager(object): 
    """
    Given a dictionary of relationships this class synchronizes
    the relevant sinks and sources
    """
    def __init__ (self, typeConverter):
        """
        Constructor. 
        
        Creates a dictionary of conduits and their status
        """
        self.conduits = {}
        self.typeConverter = typeConverter
        
    def join_all(self, timeout=None):
        """
        Joins all threads. This function will block the calling thread
        """
        for c in self.conduits:
            self.conduits[c].join(timeout)
            
    def init_conduit(self, conduit):
        """
        Just calls the initialize method on all dp's in a conduit
        """
        if conduit not in self.conduits:
            newThread = SyncWorker(self.typeConverter, conduit, (0,0))
            self.conduits[conduit] = newThread
            self.conduits[conduit].start()
                
    def sync_conduit(self, conduit):
        """
        @todo: Send some signals back to the GUI to disable clicking
        on the conduit
        @todo: Actually work out what happens if a user wants to resync 
        a conduit
        """
        if conduit not in self.conduits:
            newThread = SyncWorker(self.typeConverter, conduit)
            self.conduits[conduit] = newThread
            self.conduits[conduit].start()
        else:
            logging.warn("Conduit already in queue (alive: %s)" % self.conduits[conduit].isAlive())
            
            
class SyncWorker(threading.Thread):
    """
    Class designed to be operated within a thread used to perform the
    synchronization operation
    """
    REFRESH_STATE = 0
    SYNC_STATE = 1
    DONE_STATE = 2
    def __init__(self, typeConverter, conduit, doStates=(0,2)):
        """
        @param conduit: The conduit to synchronize
        @type conduit: L{conduit.Conduit.Conduit}
        @param typeConverter: The typeconverter
        @type typeConverter: L{conduit.TypeConverter.TypeConverter}
        """
        threading.Thread.__init__(self)
        self.typeConverter = typeConverter
        self.source = conduit.datasource
        self.sinks = conduit.datasinks
        self.state = doStates[0]
        self.finishState = doStates[1]
        
        self.setName("Synchronization Thread: %s" % conduit.datasource.get_unique_identifier())

    def run(self):
        """
        The main syncronisation state machine.
        
        Takes the conduit through the refresh->get,put,get,put->done 
        steps, setting its status at the appropriate time and performing
        nicely in the case of errors. 
        
        It is also threaded so remember
         1. Syncronization should not block the GUI
         2. Due to pygtk/gtk single threadedness do not attempt to
            communicate with the gui in any way other than signals, which
            since Glib 2.10 are threadsafe.
            
        If any error occurs during sync raise a L{conduit.Exceptions.StopSync}
        exception otherwise exit normally 

        @raise Exceptions.StopSync: Raises a L{conduit.Exceptions.StopSync} 
        exception if the synchronisation state machine does not complete, in
        some way, without success.
        """
        finished = False
        numOKSinks = 0
        while not finished:
            sourcestatus = self.source.module.get_status()        
            logging.debug("Syncworker state %s" % self.state)
            #Refresh state
            if self.state is SyncWorker.REFRESH_STATE:

                #Refresh the source
                if sourcestatus is DataProvider.STATUS_NONE:
                    try:
                        self.source.module.set_status(DataProvider.STATUS_REFRESH)
                        #Thread
                        self.source.module.refresh()
                        self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                    except Exceptions.RefreshError:
                        self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                        logging.warn("Error Refreshing: %s" % self.source)
                        #Let the calling thread know we blew it
                        raise Exceptions.StopSync
                    except Exception, err:
                        logging.warn("Unknown error refreshing: %s\n%s" % (self.source,traceback.print_exc()))
                        #Cannot continue with no source data
                        raise Exceptions.StopSync           

                #Refresh all the sinks. At least one must refresh successfully
                for sink in self.sinks:
                    sinkstatus = sink.module.get_status()                        
                    if sinkstatus is DataProvider.STATUS_NONE:
                        try:
                            sink.module.set_status(DataProvider.STATUS_REFRESH)
                            sink.module.refresh()
                            sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                            numOKSinks += 1
                        except Exceptions.RefreshError:
                            sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                            numOKSinks -= 1
                            logging.warn("Error refreshing: %s" % sink)
                        except Exception, err:
                            sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                            numOKSinks -= 1
                            logging.warn("Unknown error refreshing: %s\n%s" % (sink,traceback.format_exc()))
                            
                #Need to have at least one successfully refreshed sink            
                if numOKSinks > 0:
                    #Go to next state state
                    if self.state < self.finishState:
                        self.state += 1
                else:
                    #go home
                    finished = True

            #synchronize state
            elif self.state is SyncWorker.SYNC_STATE:
                #try and get the source data iterator
                try:
                    self.source.module.set_status(DataProvider.STATUS_SYNC)
                    sourceData = self.source.module.get()
                #if the source cannot return an iterator then its over    
                except Exceptions.SyncronizeFatalError:
                    self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                    logging.warn("Could not Get Source Data")                    
                    #Cannot continue with no source data                    
                    raise Exceptions.StopSync
                #if we dont know what happened then thats also bad programming
                except Exception, err:                        
                    self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                    logging.warn("Unknown error getting source iterator: %s\n%s" % (err,traceback.format_exc()))
                    #Cannot continue with no source data
                    raise Exceptions.StopSync           
                    
                #OK if we have got this far then we have source data to sync the sinks with             
                for sink in self.sinks:
                    sinkErrorFree = True
                    #only sync with those sinks that refresh'd OK
                    if sink.module.get_status() is DataProvider.STATUS_DONE_REFRESH_OK:

                        #Sync each piece of data one at a time
                        #FIXME how do I check that its iteratable first????
                        for data in sourceData:
                            logging.debug("Synchronizing %s -> %s (source data type = %s, sink accepts %s)" % (self.source, sink, self.source.out_type, sink.in_type))
                            try:
                                if self.source.out_type != sink.in_type:
                                    data = self.typeConverter.convert(self.source.out_type, sink.in_type, data)
                                #Finally after all the schenigans try an put the data                                
                                sink.module.put(data)
                                sink.module.set_status(DataProvider.STATUS_SYNC)
                            #Catch errors from a failed convert
                            except Exceptions.ConversionError, err:
                                #Not fatal, move along
                                logging.warn("Error converting %s" % err)
                                sinkErrorFree = False
                            except Exceptions.SynchronizeConflictError:
                                #FIXME. I imagine that implementing this is a bit of work!
                                logging.warn("Sync Conflict")                            
                            except Exceptions.SyncronizeError:
                                #non fatal, move along
                                logging.warn("Non-fatal synchronisation error")                     
                                sinkErrorFree = False                                   
                            except Exceptions.SyncronizeFatalError:
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                logging.warn("Fatal synchronisation error")            
                                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
                                #Fatal, go home       
                                raise Exceptions.StopSync                                                    
                            except Exception, err:                        
                                #Bad programmer
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                logging.warn("Unknown synchronisation error\n%s" % traceback.format_exc())
                                raise Exceptions.StopSync
                        
                        if sinkErrorFree:
                            #tell the gui if the sync was ok
                            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
                
                #Done go to next state
                if self.state < self.finishState:
                    self.state += 1

            #Done successfully go home without raising exception
            elif self.state is SyncWorker.DONE_STATE:
                finished = True
                #Tell the GUI
                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
        
