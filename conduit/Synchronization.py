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
import conduit.datatypes as DataType

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
        
    def cancel_conduit(self, conduit):
        """
        Cancel a conduit. Does not block
        """
        self.conduits[conduit].cancel()
        
    def cancel_all(self):
        """
        Cancels all threads and also joins() them. Will block
        """
        for c in self.conduits:
            self.cancel_conduit(c)
            self.conduits[c].join()            
             
    def join_all(self, timeout=None):
        """
        Joins all threads. This function will block the calling thread
        """
        for c in self.conduits:
            self.conduits[c].join(timeout)
            
    def refresh_conduit(self, conduit):
        """
        Just calls the initialize method on all dp's in a conduit
        """
        if conduit in self.conduits:
            #If the thread is alive then cancel it
            if self.conduits[conduit].isAlive():
                self.conduits[conduit].cancel()
                self.conduits[conduit].join() #Will block

        #Create a new thread over top. Thanks mr garbage collector
        newThread = SyncWorker(self.typeConverter, conduit, (0,0))
        self.conduits[conduit] = newThread
        self.conduits[conduit].start()

    def sync_conduit(self, conduit):
        """
        @todo: Send some signals back to the GUI to disable clicking
        on the conduit
        """
        if conduit in self.conduits:
            logging.warn("Conduit already in queue (alive: %s)" % self.conduits[conduit].isAlive())
            #If the thread is alive then cancel it
            if self.conduits[conduit].isAlive():
                logging.warn("Cancelling thread")
                self.conduits[conduit].cancel()
                self.conduits[conduit].join() #Will block

        #Create a new thread over top. Thanks mr garbage collector
        newThread = SyncWorker(self.typeConverter, conduit)
        self.conduits[conduit] = newThread
        self.conduits[conduit].start()
            

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
        self.cancelled = False
        
        self.setName("Synchronization Thread: %s" % conduit.datasource.get_unique_identifier())
        
    def cancel(self):
        """
        Cancels the sync thread. Does not do so immediately but as soon as
        possible.
        """
        self.cancelled = True
        
    def check_thread_not_cancelled(self, dataprovidersToCancel):
        """
        Checks if the thread has been scheduled to be cancelled. If it has
        then this function sets the status of the dataproviders to indicate
        that they were stopped through a cancel operation.
        """
        if self.cancelled:
            for s in dataprovidersToCancel:
                s.module.set_status(DataProvider.STATUS_DONE_SYNC_CANCELLED)
            raise Exceptions.StopSync

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
            self.check_thread_not_cancelled([self.source] + self.sinks)
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
                        logging.critical("Unknown error refreshing: %s\n%s" % (self.source,traceback.format_exc()))
                        #Cannot continue with no source data
                        raise Exceptions.StopSync           

                #Refresh all the sinks. At least one must refresh successfully
                for sink in self.sinks:
                    self.check_thread_not_cancelled([self.source, sink])
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
                            logging.critical("Unknown error refreshing: %s\n%s" % (sink,traceback.format_exc()))
                            
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
                    logging.critical("Unknown error getting source iterator: %s\n%s" % (err,traceback.format_exc()))
                    #Cannot continue with no source data
                    raise Exceptions.StopSync           
                
                #Because of how these loops are structured create a temp dict to
                #keep track if an error has occured in a sync
                sinkErrors = {} 
                #Sync each piece of data one at a time
                #FIXME how do I check that its iteratable first????
                for data in sourceData:
                    #OK if we have got this far then we have source data to sync the sinks with
                    #Get each piece of data and put it in each sink             
                    for sink in self.sinks:
                        self.check_thread_not_cancelled([self.source, sink])
                        #only sync with those sinks that refresh'd OK
                        if sink.module.get_status() in [DataProvider.STATUS_DONE_REFRESH_OK, DataProvider.STATUS_SYNC]:
                            logging.debug("Synchronizing %s -> %s (source \
                                            data type = %s, sink accepts %s)" % 
                                            (self.source, sink, 
                                            self.source.out_type, sink.in_type))
                            try:
                                if self.source.out_type != sink.in_type:
                                    if self.typeConverter.conversion_exists(self.source.out_type, sink.in_type):
                                        newdata = self.typeConverter.convert(self.source.out_type, sink.in_type, data)
                                    else:
                                        raise Exceptions.ConversionDoesntExistError
                                else:
                                    newdata = data

                                #Finally after all the schenigans try an put the data. If there is
                                #a conflict then this will raise a conflict error. This code would be nicer
                                #if python had supported the retry keyword.
                                sink.module.set_status(DataProvider.STATUS_SYNC)
                                finishedPutting = False
                                while not finishedPutting:
                                    try:
                                        sink.module.put(newdata)
                                        finishedPutting = True
                                    except Exceptions.SynchronizeConflictError, err:
                                        #unpack args
                                        #(comparison, fromData, toData, datasink) = err
                                        logging.debug(err)
                                        #Have tried put() one way (and it failed, geting us here). 
                                        #Only try once the other way (and only if supported)
                                        #Do not loop forever
                                        finishedPutting = True
                                        if self.source.two_way:
                                            #If the comparison was the other way then
                                            if err.comparison == DataType.COMPARISON_OLDER:
                                                logging.debug("Sync Conflict: Putting OLD Data")
                                            elif err.comparison == DataType.COMPARISON_EQUAL or err.comparison == DataType.COMPARISON_UNKNOWN:
                                                #FIXME. I imagine that implementing this is a bit of work!
                                                #The data needs to get back to the main gui thread safely...
                                                logging.warn("Sync Conflict: Putting EQUAL or UNKNOWN Data")
                                        #Nothing we can do 
                                        else:
                                            logging.error("Sync Conflict: Cannot resolve conflict, source does not support put()")
   
                            #Catch exceptions if we abort the sync cause no conversion exists
                            except Exceptions.ConversionDoesntExistError:
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_SKIPPED)
                                sinkErrors[sink] = True
                            #Catch errors from a failed convert
                            except Exceptions.ConversionError, err:
                                #Not fatal, move along
                                logging.warn("Error converting %s" % err)
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                sinkErrors[sink] = True
                            except Exceptions.SyncronizeError:
                                #non fatal, move along
                                logging.warn("Non-fatal synchronisation error")                     
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                sinkErrors[sink] = True
                            except Exceptions.SyncronizeFatalError:
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                logging.warn("Fatal synchronisation error")            
                                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
                                #Fatal, go home       
                                raise Exceptions.StopSync                                                    
                            except Exception, err:                        
                                #Bad programmer
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                logging.critical("Unknown synchronisation error\n%s" % traceback.format_exc())
                                raise Exceptions.StopSync
                
                #Now go back and check for errors
                for sink in self.sinks:
                    if sink not in sinkErrors:
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
        
