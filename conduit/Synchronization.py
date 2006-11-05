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
            #Thanks mr garbage collector    
            del(self.conduits[conduit])

        #Create a new thread over top
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
            #Thanks mr garbage collector    
            del(self.conduits[conduit])

        #Create a new thread over top.
        newThread = SyncWorker(self.typeConverter, conduit, (0,1))
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
            
    def _convert_data(self, fromType, toType, data):
        """
        Converts and returns data from fromType to toType.
        Handles all errors nicely and returns none on error
        """
        try:
            if fromType != toType:
                if self.typeConverter.conversion_exists(fromType, toType):
                    newdata = self.typeConverter.convert(fromType, toType, data)
                else:
                    newdata = None
                    raise Exceptions.ConversionDoesntExistError
                    
            else:
                newdata = data
        #Catch exceptions if we abort the sync cause no conversion exists
        except Exceptions.ConversionDoesntExistError:
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_SKIPPED
        #Catch errors from a failed convert
        except Exceptions.ConversionError, err:
            #Not fatal, move along
            logging.warn("Error converting %s" % err)
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR

        return newdata


    def _put_data(self, dataproviderWrapper, data):
        """
        Puts data into dataproviderModule and handles 
        non fatal exceptions gracefully.
        """
        try:
            #Puts the data, providing it is newer
            dataproviderWrapper.module.put(data)
        except Exceptions.SynchronizeConflictError, err:
            #unpack args
            #(comparison, fromData, toData, datasink) = err
            if err.comparison == DataType.COMPARISON_OLDER:
                logging.debug("Sync Conflict: Skipping OLD Data\n%s" % err)
            #If the data could not be compared then the user must decide
            elif err.comparison == DataType.COMPARISON_EQUAL or err.comparison == DataType.COMPARISON_UNKNOWN:
                #FIXME. I imagine that implementing this is a bit of work!
                #The data needs to get back to the main gui thread safely
                #so that the user can decide... Perhaps a signal???
                logging.warn("Sync Conflict: Putting EQUAL or UNKNOWN Data")
                self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            #This should not happen...
            else:
                logging.critical("Unknown comparison (BAD PROGRAMMER)\n%s" % traceback.format_exc())
                self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            
    def one_way_sync(self, source, sink, numItems):
        """
        Transfers numItems of data from source to sink
        """
        logging.debug("Synchronizing %s |--> %s " % (source, sink))
        for i in range(0, numItems):
            data = source.module.get(i)
            #all non fatal errors are handled by _put_data and convert_data
            #so all that we need to care about are fatal errors
            try:
                #convert data type if necessary
                newdata = self._convert_data(source.out_type, sink.in_type, data)
                #store it 
                if newdata != None:
                    self._put_data(sink, newdata)
            except Exceptions.SyncronizeError, err:
                #non fatal, move along
                logging.warn("Error synchronizing %s", err)                     
                self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
            except Exceptions.SyncronizeFatalError, err:
                #Fatal, go home       
                logging.warn("Error synchronizing %s", err)
                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                                  
                source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
                raise Exceptions.StopSync                  
            except Exception, err:                        
                #Fatal, go home       
                logging.critical("Unknown synchronisation error (BAD PROGRAMMER)\n%s" % traceback.format_exc())
                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                raise Exceptions.StopSync

        
    def two_way_sync(self, source, sink, numItems):
        logging.debug("Synchronizing %s <--> %s " % (source, sink))

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
        #Variable to exit the loop
        finished = False
        #Because of how these loops are structured create a temp dict to
        #keep track if an error has occured in a sync, or in refresh
        sinkErrors = {}
        #Keep track of those sinks that didnt refresh ok
        sinkDidntRefreshOK = {}
        
        #Error handling is a bit complex because we need to send
        #signals back to the gui for display, and because some errors
        #are not fatal. If there is an error, set the 
        #'working' statuses immediately (Sync, Refresh) and set the 
        #Negative status (error, conflict, etc) at the end so they remain 
        #on the GUI and the user can see them.
        #UNLESS the error is Fatal (causes us to throw a stopsync exceptiion)
        #in which case set the error status immediately.

        while not finished:
            self.check_thread_not_cancelled([self.source] + self.sinks)
            logging.debug("Syncworker state %s" % self.state)
            #Refresh state
            if self.state is SyncWorker.REFRESH_STATE:
                logging.debug("Source Status = %s" % self.source.module.get_status_text())
                #Refresh the source
                try:
                    self.source.module.set_status(DataProvider.STATUS_REFRESH)
                    self.source.module.refresh()
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                except Exceptions.RefreshError:
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                    logging.critical("Error Refreshing: %s" % self.source)
                    #Cannot continue with no source data
                    raise Exceptions.StopSync
                except Exception, err:
                    logging.critical("Unknown error refreshing: %s\n%s" % (self.source,traceback.format_exc()))
                    #Cannot continue with no source data
                    raise Exceptions.StopSync           

                #Refresh all the sinks. At least one must refresh successfully
                for sink in self.sinks:
                    self.check_thread_not_cancelled([self.source, sink])
                    try:
                        sink.module.set_status(DataProvider.STATUS_REFRESH)
                        sink.module.refresh()
                        sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                    except Exceptions.RefreshError:
                        logging.warn("Error refreshing: %s" % sink)
                        sinkDidntRefreshOK[sink] = True
                        sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                    except Exception, err:
                        logging.critical("Unknown error refreshing: %s\n%s" % (sink,traceback.format_exc()))
                        sinkDidntRefreshOK[sink] = True
                        sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                            
                #Need to have at least one successfully refreshed sink            
                if len(sinkErrors) < len(self.sinks):
                    #Go to next state state
                    if self.state < self.finishState:
                        self.state += 1
                    else:
                        self.state = SyncWorker.DONE_STATE                        
                else:
                    #go home
                    finished = True

            #synchronize state
            elif self.state is SyncWorker.SYNC_STATE:
                try:
                    self.source.module.set_status(DataProvider.STATUS_SYNC)
                    #Depending on the dp, this call make take a while as it may need
                    #to get all the data to tell how many items there are...
                    numItems = self.source.module.get_num_items()
                #if the source errors then its not worth doing anything to the sink
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
                
                for sink in self.sinks:
                    self.check_thread_not_cancelled([self.source, sink])
                    #only sync with those sinks that refresh'd OK
                    if sink not in sinkDidntRefreshOK:
                        #now perform a one or two way sync depending on the user prefs
                        #and the capabilities of the dataprovider
                        #FIXME: Check the dataproviders are capable and the conduit has two way enabled
                        if  False: ##self.conduit.is_two_way_sync_enabled(self.source, sink): ## && conduit.two_way_enabled...
                            #two way
                            self.two_way_sync(self.source, sink, numItems)
                        else:
                            #one way
                            self.one_way_sync(self.source, sink, numItems)
 
                #Done go to next state
                if self.state < self.finishState:
                    self.state += 1
                else:
                    self.state = SyncWorker.DONE_STATE

            #Done successfully go home without raising exception
            elif self.state is SyncWorker.DONE_STATE:
                #Now go back and check for errors, so that we can tell the GUI
                #First update those sinks which had no errors
                for sink in self.sinks:
                    if sink not in sinkErrors:
                        #tell the gui if the sync was ok
                        sink.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
                #Then those sinks which had some error
                for sink in sinkErrors:
                    sink.module.set_status(sinkErrors[sink])
                
                #It is safe to put this call here because all other source related
                #Errors raise a StopSync exception and the thread exits
                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
                
                #Exit thread
                finished = True
                
        
