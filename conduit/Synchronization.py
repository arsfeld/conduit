"""
Holds class used for the actual synchronisation phase

Copyright: John Stowers, 2006
License: GPLv2
"""

import traceback
import threading
import gobject

import conduit
from conduit import log,logd,logw

import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.DB as DB
import conduit.Utils as Utils

from conduit.Conflict import CONFLICT_COPY_SOURCE_TO_SINK,CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE
from conduit.datatypes import DataType, COMPARISON_OLDER, COMPARISON_EQUAL, COMPARISON_NEWER, COMPARISON_OLDER, COMPARISON_UNKNOWN

class SyncManager: 
    """
    Given a dictionary of relationships this class synchronizes
    the relevant sinks and sources. If there is a conflict then this is
    handled by the conflictResolver
    """
    def __init__ (self, typeConverter):
        """
        Constructor. 
        
        Creates a dictionary of syncWorkers indexed by conduit
        """
        self.syncWorkers = {}
        self.typeConverter = typeConverter

        #The mapping DB is shared conduit wide
        self.mappingDB = conduit.mappingDB

        #Callback functions that syncworkers call. Saves having to make this
        #inherit from gobject and re-pass all the signals
        self.syncStartedCbs = []
        self.syncCompleteCbs = []
        self.syncConflictCbs = []

        #Two way sync policy
        self.policy = {"conflict":"ask","deleted":"ask"}

    def _connect_sync_thread_callbacks(self, thread):
        for cb in self.syncStartedCbs:
            thread.connect("sync-started", cb)
        for cb in self.syncCompleteCbs:
            thread.connect("sync-completed", cb)
        for cb in self.syncConflictCbs:
            thread.connect("sync-conflict", cb)

        return thread

    def add_syncworker_callbacks(self, syncStartedCb, syncCompleteCb, syncConflictCb):
        """
        Sets the callbacks that are called by the SyncWorker threads
        upon the specified conditions
        """
        if syncStartedCb != None and syncStartedCb not in self.syncStartedCbs:
            self.syncStartedCbs.append(syncStartedCb)
        if syncCompleteCb != None and syncCompleteCb not in self.syncCompleteCbs:
            self.syncCompleteCbs.append(syncCompleteCb)
        if syncConflictCb != None and syncConflictCb not in self.syncConflictCbs:
            self.syncConflictCbs.append(syncConflictCb)

    def set_twoway_policy(self, policy):
        logd("Setting sync policy: %s" % policy)
        self.policy = policy
        #It is NOT threadsafe to apply to existing conduits

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
            """
        if conduit in self.syncWorkers:
            #If the thread is alive then cancel it
            if self.syncWorkers[conduit].isAlive():
                self.syncWorkers[conduit].cancel()
                self.syncWorkers[conduit].join() #Will block
            #Thanks mr garbage collector    
            del(self.syncWorkers[conduit])

        #Create a new thread over top
        newThread = SyncWorker(self.typeConverter, self.mappingDB, conduit, False, self.policy)
        self.syncWorkers[conduit] = newThread
        self.syncWorkers[conduit].start()

    def sync_conduit(self, conduit):
        """
        @todo: Send some signals back to the GUI to disable clicking
        on the conduit
        """
        if conduit in self.syncWorkers:
            logw("Conduit already in queue (alive: %s)" % self.syncWorkers[conduit].isAlive())
            #If the thread is alive then cancel it
            if self.syncWorkers[conduit].isAlive():
                logw("Cancelling thread")
                self.syncWorkers[conduit].cancel()
                self.syncWorkers[conduit].join() #Will block
            #Thanks mr garbage collector    
            del(self.syncWorkers[conduit])

        #Create a new thread over top.
        newThread = SyncWorker(self.typeConverter, self.mappingDB, conduit, True, self.policy)
        #Connect the callbacks
        self.syncWorkers[conduit] = self._connect_sync_thread_callbacks(newThread)
        self.syncWorkers[conduit].start()
            

class SyncWorker(threading.Thread, gobject.GObject):
    """
    Class designed to be operated within a thread used to perform the
    synchronization operation. Inherits from GObject because it uses 
    signals to communcate with the main GUI.

    Operates on a per Conduit basis, so a single SyncWorker may synchronize
    one source with many sinks within a single conduit
    """
    CONFIGURE_STATE = 0
    REFRESH_STATE = 1
    SYNC_STATE = 2
    DONE_STATE = 3

    __gsignals__ =  { 
                    "sync-conflict": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT,      #datasource wrapper
                        gobject.TYPE_PYOBJECT,      #from data
                        gobject.TYPE_PYOBJECT,      #datasink wrapper
                        gobject.TYPE_PYOBJECT,      #to data
                        gobject.TYPE_PYOBJECT,      #valid resolve choices
                        gobject.TYPE_BOOLEAN]),     #Is the conflict from a deletion
                    "sync-completed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "sync-started": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    def __init__(self, typeConverter, mappingDB, conduit, do_sync, policy):
        """
        @param conduit: The conduit to synchronize
        @type conduit: L{conduit.Conduit.Conduit}
        @param typeConverter: The typeconverter
        @type typeConverter: L{conduit.TypeConverter.TypeConverter}
        """
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.typeConverter = typeConverter
        self.mappingDB = mappingDB
        self.conduit = conduit
        self.source = conduit.datasource
        self.sinks = conduit.datasinks
        self.do_sync = do_sync
        self.policy = policy

        #Keep track of any errors in the sync process. Class variable because these
        #may occur in a data conversion. Needed so that the correct status
        #is shown on the GUI at the end of the sync process
        self.sinkErrors = {}

        #Start at the beginning
        self.state = SyncWorker.CONFIGURE_STATE
        self.cancelled = False

        if conduit.is_two_way():
            self.setName("%s <--> %s" % (self.source, self.sinks[0]))
        else:
            self.setName("%s |--> %s" % (self.source, self.sinks))
    def _convert_data(self, sink, fromType, toType, data):
        """
        Converts and returns data from fromType to toType.
        Handles all errors nicely and returns none on error
        """
        newdata = None

        if fromType != toType:
            if self.typeConverter.conversion_exists(fromType, toType):
                newdata = self.typeConverter.convert(fromType, toType, data)
            else:
                newdata = None
                raise Exceptions.ConversionDoesntExistError
        else:
            newdata = data

        return newdata

    def _put_data(self, source, sink, data, overwrite):
        """
        Puts data into sink, overwrites if overwrite is True
        """            
        LUID, mtime = self.mappingDB.get_mapping(
                                sourceUID=source.get_UID(),
                                sourceDataLUID=data.get_UID(),
                                sinkUID=sink.get_UID()
                                )
        #Unless the user has selected slow_sync only put data whose mtime has
        #changed
        if data.get_mtime() != mtime or self.conduit.do_slow_sync():
            LUID = sink.module.put(data, overwrite, LUID)
            mtime = data.get_mtime()
            #Now store the mapping of the original URI to the new one. We only
            #get here if the put was successful, so the mtime of the putted
            #data wll be the same as the original data
            self.mappingDB.save_mapping(
                                    sourceUID=source.get_UID(),
                                    sourceDataLUID=data.get_UID(),
                                    sinkUID=sink.get_UID(),
                                    sinkDataLUID=LUID,
                                    mtime=mtime
                                    )
        else:
            logd("Skipping %s. Mtimes has not changed (actual %s v saved %s)" % (data.get_UID(), data.get_mtime(), mtime))

    def _apply_deleted_policy(self, sourceWrapper, sinkWrapper, dataLUID, leftToRight):
        """
        Applies user policy when data has been deleted from source.
        Assumes that source is on the left (visually) unless
        leftToRight is False
        """
        logd("DELETE SUPPORT NOT FINSHED")
        return
        if self.policy["deleted"] == "skip":
            logd("Deleted Policy: Skipping")
        elif self.policy["deleted"] == "ask":
            logd("Deleted Policy: Ask")
            if leftToRight == True:
                validResolveChoices = (CONFLICT_COPY_SINK_TO_SOURCE,CONFLICT_SKIP)
            else:
                validResolveChoices = (CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE)
            self.emit("sync-conflict", 
                        sourceWrapper,              #datasource wrapper
                        DeletedData(dataLUID),      #from data
                        sinkWrapper,                #datasink wrapper
                        DeletedData(None),          #to data
                        validResolveChoices,        #valid resolve choices
                        True                        #This conflict is a deletion
                        )
        elif self.policy["deleted"] == "replace":
            logd("Deleted Policy: Replace (Delete corresponding data)")
            self.sinkWrapper.module.delete(dataLUID)
            self.mappingDB.delete_mappings(
                                sourceUID=sourceWrapper.get_UID(),
                                sourceDataLUID=dataLUID,
                                sinkUID=sinkWrapper.get_UID()
                                )
         
    def _apply_conflict_policy(self, sourceWrapper, sinkWrapper, comparison, fromData, toData):
        """
        Applies user policy when a put() has failed. This may mean emitting
        the conflict up to the GUI or skipping altogether
        """
        if comparison == COMPARISON_EQUAL or comparison == COMPARISON_UNKNOWN or comparison == COMPARISON_OLDER:
            log("CONFLICT: Putting EQUAL or UNKNOWN or OLDER Data")
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            if self.policy["conflict"] == "skip":
                logd("Conflict Policy: Skipping")
            elif self.policy["conflict"] == "ask":
                logd("Conflict Policy: Ask")
                self.emit("sync-conflict", 
                            sourceWrapper, 
                            fromData, 
                            sinkWrapper, 
                            toData, 
                            (0,1,2),
                            False
                            )
            elif self.policy["conflict"] == "replace":
                logd("Conflict Policy: Replace")
                try:
                    self._put_data(sourceWrapper, sinkWrapper, toData, True)
                except:
                    logw("Forced Put Failed\n%s" % traceback.format_exc())        
        #This should not happen...
        else:
            logw("Unknown comparison (BAD PROGRAMMER)\n%s" % traceback.format_exc())
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT

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

    def one_way_sync(self, source, sink, skipOlder, leftToRight):
        """
        Transfers numItems of data from source to sink. Does not consider 
        if either is a slow sync or not. That is handled in put_data. This 
        function only serves as a means to deal with exceptions and policy
        """
        numItems = source.module.get_num_items()
        #Detecting items which have been deleted involves comparing the
        #data LUIDs which are returned from the get() with those 
        #that were synchronized last time
        existing = [i["sourceDataLUID"] for i in self.mappingDB.get_mappings_for_dataproviders(source.get_UID(), sink.get_UID())]

        if leftToRight == True:
            log("Synchronizing %s |--> %s " % (source, sink))
        else:
            log("Synchronizing %s <--| %s " % (source, sink))

        for i in range(0, numItems):
            data = source.module.get(i)
            try:
                #convert data type if necessary
                newdata = self._convert_data(sink, source.get_out_type(), sink.get_in_type(), data)
                try:
                    self._put_data(source, sink, newdata, False)
                except Exceptions.SynchronizeConflictError, err:
                    comp = err.comparison
                    if comp == COMPARISON_OLDER and skipOlder:
                        logd("Skipping %s (Older)", newdata)
                        pass
                    elif comp == COMPARISON_EQUAL:
                        logd("Skipping %s (Equal)", newdata)
                        pass
                    else:
                        self._apply_conflict_policy(source, sink, err.comparison, err.fromData, err.toData)

                #now remove from the list of expected data to synchronize
                if existing.count(newdata.get_UID()):
                    existing.remove(newdata.get_UID())

            except Exceptions.ConversionDoesntExistError:
                logd("No Conversion Exists")
                self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_SKIPPED
            except Exceptions.ConversionError, err:
                logw("Error converting %s" % err)
                self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
            except Exceptions.SyncronizeError, err:
                logw("Error synchronizing %s", err)                     
                self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
            except Exceptions.SyncronizeFatalError, err:
                logw("Error synchronizing %s", err)
                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                                  
                source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
                #Cannot continue
                raise Exceptions.StopSync                  
            except Exception, err:                        
                #Cannot continue
                logw("Unknown synchronisation error\n%s" % traceback.format_exc())
                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                raise Exceptions.StopSync

        #give dataproviders the freedom to also provide a list of deleted 
        #data UIDs.
        deleted = Utils.distinct_list(existing + source.module.get_deleted_items())
        logd("There were %s deleted items" % len(deleted))
        for d in deleted:
            self._apply_deleted_policy(source, sink, d, leftToRight)
       
    def two_way_sync(self, source, sink):
        """
        Performs a two way sync from source to sink and back.
        """
        log("Synchronizing %s <--> %s " % (source, sink))
        self.one_way_sync(source, sink, True, True)
        self.one_way_sync(sink, source, True, False)

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
        logd("Sync %s beginning. Slow: %s, Twoway: %s" % (
                                self,
                                self.conduit.do_slow_sync(), 
                                self.conduit.is_two_way()
                                ))
        #Variable to exit the loop
        finished = False
        #Keep track of those sinks that didnt refresh ok
        sinkDidntRefreshOK = {}
        sinkDidntConfigureOK = {}
        
        #Error handling is a bit complex because we need to send
        #signals back to the gui for display, and because some errors
        #are not fatal. If there is an error, set the 
        #'working' statuses immediately (Sync, Refresh) and set the 
        #Negative status (error, conflict, etc) at the end so they remain 
        #on the GUI and the user can see them.
        #UNLESS the error is Fatal (causes us to throw a stopsync exceptiion)
        #in which case set the error status immediately.
        self.emit("sync-started")
        while not finished:
            self.check_thread_not_cancelled([self.source] + self.sinks)
            logd("Syncworker state %s" % self.state)

            #Check dps have been configured
            if self.state is SyncWorker.CONFIGURE_STATE:
                if not self.source.module.is_configured():
                    self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_NOT_CONFIGURED)
                    #Cannot continue if source not configured
                    raise Exceptions.StopSync
    
                for sink in self.sinks:
                    if not sink.module.is_configured():
                        sinkDidntConfigureOK[sink] = True
                        self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_NOT_CONFIGURED
                #Need to have at least one successfully configured sink
                if len(sinkDidntConfigureOK) < len(self.sinks):
                    #If this thread is a sync thread do a sync
                    self.state = SyncWorker.REFRESH_STATE
                else:
                    #We are finished
                    print "NOT ENOUGHT CONFIGURED OK"
                    self.state = SyncWorker.DONE_STATE                  

            #refresh state
            elif self.state is SyncWorker.REFRESH_STATE:
                logd("Source Status = %s" % self.source.module.get_status_text())
                #Refresh the source
                try:
                    self.source.module.refresh()
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                except Exceptions.RefreshError:
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                    logw("Error Refreshing: %s" % self.source)
                    #Cannot continue with no source data
                    raise Exceptions.StopSync
                except Exception, err:
                    self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                    logw("Unknown error refreshing: %s\n%s" % (self.source,traceback.format_exc()))
                    #Cannot continue with no source data
                    raise Exceptions.StopSync           

                #Refresh all the sinks. At least one must refresh successfully
                for sink in self.sinks:
                    self.check_thread_not_cancelled([self.source, sink])
                    if sink not in sinkDidntConfigureOK:
                        try:
                            sink.module.refresh()
                            sink.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                        except Exceptions.RefreshError:
                            logw("Error refreshing: %s" % sink)
                            sinkDidntRefreshOK[sink] = True
                            self.sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                        except Exception, err:
                            logw("Unknown error refreshing: %s\n%s" % (sink,traceback.format_exc()))
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
                for sink in self.sinks:
                    self.check_thread_not_cancelled([self.source, sink])
                    #only sync with those sinks that refresh'd OK
                    if sink not in sinkDidntRefreshOK:
                        #now perform a one or two way sync depending on the user prefs
                        #and the capabilities of the dataprovider
                        if  self.conduit.is_two_way():
                            #two way
                            self.two_way_sync(self.source, sink)
                        else:
                            #one way
                            self.one_way_sync(self.source, sink, False, True)
 
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

        self.mappingDB.save()
        self.emit("sync-completed")
                
class DeletedData(DataType.DataType):
    """
    Simple wrapper around a deleted item. If an item has been deleted then
    we can no longer rely on its open_URI, and we must fall back to a 
    plain string object
    """
    def __init__(self, UID, **kwargs):
        self.UID = UID
        self.snippet = kwargs.get("snippet", "Deleted from %s" % self.UID)

    def get_UID(self):
        return self.UID
        
    def get_snippet(self):
        return self.snippet

    def get_open_URI(self):
        return None

    def __str__(self):
        return "Deleted Data: %s" % self.UID
