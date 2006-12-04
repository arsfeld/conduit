"""
Holds class used for the actual synchronisation phase

Copyright: John Stowers, 2006
License: GPLv2
"""

import traceback
import threading
import gobject

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes as DataType

class SyncManager(object): 
    """
    Given a dictionary of relationships this class synchronizes
    the relevant sinks and sources. If there is a conflict then this is
    handled by the conflictResolver
    """
    def __init__ (self, typeConverter, conflictResolver=None):
        """
        Constructor. 
        
        Creates a dictionary of syncWorkers indexed by conduit
        """
        self.syncWorkers = {}
        self.typeConverter = typeConverter
        self.conflictResolver = conflictResolver
        
    def cancel_conduit(self, conduit):
        """
        Cancel a conduit. Does not block
        """
        self.syncWorkers[conduit].cancel()
        
    def cancel_all(self):
        """
        Cancels all threads and also joins() them. Will block
        """
        for c in self.syncWorkers:
            self.cancel_conduit(c)
            self.syncWorkers[c].join()            
             
    def join_all(self, timeout=None):
        """
        Joins all threads. This function will block the calling thread
        """
        for c in self.syncWorkers:
            self.syncWorkers[c].join(timeout)
            
    def refresh_conduit(self, conduit):
        """
        Just calls the initialize method on all dp's in a conduit
        """
        if conduit in self.syncWorkers:
            #If the thread is alive then cancel it
            if self.syncWorkers[conduit].isAlive():
                self.syncWorkers[conduit].cancel()
                self.syncWorkers[conduit].join() #Will block
            #Thanks mr garbage collector    
            del(self.syncWorkers[conduit])

        #Create a new thread over top
        newThread = SyncWorker(self.typeConverter, conduit, False)
        self.syncWorkers[conduit] = newThread
        self.syncWorkers[conduit].start()

    def sync_conduit(self, conduit):
        """
        @todo: Send some signals back to the GUI to disable clicking
        on the conduit
        """
        if conduit in self.syncWorkers:
            logging.warn("Conduit already in queue (alive: %s)" % self.syncWorkers[conduit].isAlive())
            #If the thread is alive then cancel it
            if self.syncWorkers[conduit].isAlive():
                logging.warn("Cancelling thread")
                self.syncWorkers[conduit].cancel()
                self.syncWorkers[conduit].join() #Will block
            #Thanks mr garbage collector    
            del(self.syncWorkers[conduit])

        #Create a new thread over top.
        newThread = SyncWorker(self.typeConverter, conduit, True)
        self.syncWorkers[conduit] = newThread
        self.syncWorkers[conduit].start()
            

class SyncWorker(threading.Thread, gobject.GObject):
    """
    Class designed to be operated within a thread used to perform the
    synchronization operation. Inherits from GObject because it uses 
    signals to communcate with the main GUI.
    """
    REFRESH_STATE = 0
    SYNC_STATE = 1
    DONE_STATE = 2

    TWO_WAY_DELETE_A = 0
    TWO_WAY_DELETE_B = 1
    TWO_WAY_OVER_A = 2
    TWO_WAY_OVER_B = 3
    TWO_WAY_ASK = 4

    __gsignals__ =  { 
                    "sync-conflict": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "sync-completed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    def __init__(self, typeConverter, conduit, do_sync):
        """
        @param conduit: The conduit to synchronize
        @type conduit: L{conduit.Conduit.Conduit}
        @param typeConverter: The typeconverter
        @type typeConverter: L{conduit.TypeConverter.TypeConverter}
        """
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.typeConverter = typeConverter
        self.conduit = conduit
        self.source = conduit.datasource
        self.sinks = conduit.datasinks
        self.do_sync = do_sync

        #Keep track of any errors in the syn process. Class variable because these
        #may occur in a data conversion. Needed so that the correct status
        #is shown on the GUI at the end of the sync process
        self.sinkErrors = {}

        #Start at the beginning
        self.state = SyncWorker.REFRESH_STATE
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
            
    def _compare_data_with_policy(self, A, B, policy={}):
        """
        Compares A with B and returns what the sync thread should do.
        """
        #TWO_WAY_DELETE_A = 0
        #TWO_WAY_DELETE_B = 1
        #TWO_WAY_OVER_A = 2
        #TWO_WAY_OVER_B = 3
        return SyncWorker.TWO_WAY_ASK

    def _convert_data(self, sink, fromType, toType, data):
        """
        Converts and returns data from fromType to toType.
        Handles all errors nicely and returns none on error
        """
        newdata = None

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
                self.sinkErrors[dataproviderWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            #This should not happen...
            else:
                logging.critical("Unknown comparison (BAD PROGRAMMER)\n%s" % traceback.format_exc())
                self.sinkErrors[dataproviderWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            
    def one_way_sync(self, source, sink, numItems):
        """
        Transfers numItems of data from source to sink
        """
        logging.info("Synchronizing %s |--> %s " % (source, sink))
        for i in range(0, numItems):
            data = source.module.get(i)
            #all non fatal errors are handled by _put_data and convert_data
            #so all that we need to care about are fatal errors
            try:
                #convert data type if necessary
                newdata = self._convert_data(sink, source.out_type, sink.in_type, data)
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
        """
        Performs a two way sync from source to sink and back

        General approach
         1. Get items from source, store them in a dict indexed by data UID
         2. Get all items from B, store them in a dict indexed by data UID
         3. Classify data, two sub cases
            a. If data is in one and not the other then transfer
            b. If data is in both then compare, applying the users policy
            c. If data is in both and comparison is unknown then ask user
        """
        logging.info("Synchronizing %s <--> %s " % (source, sink))
        
        #Holds Data items indexed by UID
        sourceItems = {}
        sinkItems = {}

        #Get all the data
        for i in range(0, source.module.get_num_items()):
            data = source.module.get(i)
            sourceItems[data.UID] = (data, i)
        for i in range(0, sink.module.get_num_items()):
            data = sink.module.get(i)
            sinkItems[data.UID] = (data, i)
        
        #Build a list of items missing from the other, List contains a tuple of
        #(the data, the place where its going)
        missing = []
        missing += [(sinkItems[i][0],source) for i in sinkItems.keys() if i not in sourceItems]
        missing += [(sourceItems[i][0],sink) for i in sourceItems.keys() if i not in sinkItems]
        for data,dest in missing:
            #FIXME: Apply user policy
            #dest.module.put(data)
            logging.debug("MISSING: %s FROM %s" % (data, dest))

        #Build a list of conflicts (Items in both) - from the perspective of the source
        for key in [i for i in sinkItems.keys() if i in sourceItems]:
            #source is a
            aData, aIndex = sourceItems[key]
            #sink is b
            bData, bIndex = sinkItems[key]
            logging.debug("CONFLICT: %s" % key)
            #FIXME: Apply policy
            compare = self._compare_data_with_policy(A=aData,B=bData)
            if compare == SyncWorker.TWO_WAY_DELETE_A:
                #source.delete(aIndex)
                pass
            elif compare == SyncWorker.TWO_WAY_DELETE_B:
                #sink.delete(bIndex)
                pass
            elif compare == SyncWorker.TWO_WAY_OVER_A:
                #sink.put(source.get(bIndex),aIndex,onTop=True)
                pass
            elif compare == SyncWorker.TWO_WAY_OVER_B:
                #source.put(sink.get(aIndex),bIndex,onTop=True)
                pass
            else:
                #SyncWorker.TWO_WAY_ASK
                #self.emit("conflict",source.name, sink.name, fromData, fromIndex, toData, toIndex)
                logging.debug("CONFLICT: Asking user")

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
                    self.source.module.refresh()
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                except Exceptions.RefreshError:
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                    logging.critical("Error Refreshing: %s" % self.source)
                    #Cannot continue with no source data
                    raise Exceptions.StopSync
                except Exception, err:
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                    logging.critical("Unknown error refreshing: %s\n%s" % (self.source,traceback.format_exc()))
                    #Cannot continue with no source data
                    raise Exceptions.StopSync           

                #Refresh all the sinks. At least one must refresh successfully
                for sink in self.sinks:
                    self.check_thread_not_cancelled([self.source, sink])
                    try:
                        sink.module.refresh()
                        sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                    except Exceptions.RefreshError:
                        logging.warn("Error refreshing: %s" % sink)
                        sinkDidntRefreshOK[sink] = True
                        self.sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                    except Exception, err:
                        logging.critical("Unknown error refreshing: %s\n%s" % (sink,traceback.format_exc()))
                        sinkDidntRefreshOK[sink] = True
                        self.sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                            
                #Need to have at least one successfully refreshed sink            
                if len(sinkDidntRefreshOK) < len(self.sinks):
                    #If this thread is a sync thread do a sync
                    if self.do_sync:
                        self.state = SyncWorker.SYNC_STATE
                    else:
                        #This must be a refresh thread so we are done
                        self.state = SyncWorker.DONE_STATE                        
                else:
                    #We are finished
                    print "NOT ENOUGHT REFRESHED OK"
                    self.state = SyncWorker.DONE_STATE                        

            #synchronize state
            elif self.state is SyncWorker.SYNC_STATE:
                try:
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
                        if  self.conduit.is_two_way():
                            #two way
                            self.two_way_sync(self.source, sink, numItems)
                        else:
                            #one way
                            self.one_way_sync(self.source, sink, numItems)
 
                #Done go clean up
                self.state = SyncWorker.DONE_STATE

            #Done successfully go home without raising exception
            elif self.state is SyncWorker.DONE_STATE:
                #Now go back and check for errors, so that we can tell the GUI
                #First update those sinks which had no errors
                for sink in self.sinks:
                    if sink not in self.sinkErrors:
                        #Tell the gui if things went OK.
                        if self.do_sync:
                            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
                        else:
                            sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                #Then those sinks which had some error
                for sink in self.sinkErrors:
                    sink.module.set_status(self.sinkErrors[sink])
                
                #It is safe to put this call here because all other source related
                #Errors raise a StopSync exception and the thread exits
                if self.do_sync:
                    self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
                else:
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                
                # allow dataproviders to do any post-sync cleanup
                for s in [self.source] + self.sinks:
                    s.module.finish()        
                
                #Exit thread
                finished = True
                
