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
import conduit.DeltaProvider as DeltaProvider

from conduit.Conflict import CONFLICT_DELETE, CONFLICT_COPY_SOURCE_TO_SINK,CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE
from conduit.datatypes import DataType, COMPARISON_OLDER, COMPARISON_EQUAL, COMPARISON_NEWER, COMPARISON_OLDER, COMPARISON_UNKNOWN

def _put_data(source, sink, data, LUID, overwrite):
    """
    Puts data into sink, overwrites if overwrite is True. Updates 
    the mappingDB
    """
    log("Putting data %s into %s" % (data.get_UID(), sink.get_UID()))
    LUID = sink.module.put(data, overwrite, LUID)
    mtime = data.get_mtime()
    #Now store the mapping of the original URI to the new one. We only
    #get here if the put was successful, so the mtime of the putted
    #data wll be the same as the original data
    conduit.mappingDB.save_mapping(
                            sourceUID=source.get_UID(),
                            sourceDataLUID=data.get_UID(),
                            sourceDataMtime=mtime,
                            sinkUID=sink.get_UID(),
                            sinkDataLUID=LUID,
                            sinkDataMtime=mtime
                            )

def _delete_data(source, sink, dataLUID):
    """
    Deletes data from sink and updates the mapping DB
    """
    log("Deleting %s from %s" % (dataLUID, sink.get_UID()))
    sink.module.delete(dataLUID)
    conduit.mappingDB.delete_mapping(
                        sourceUID=source.get_UID(),
                        dataLUID=dataLUID,
                        sinkUID=sink.get_UID()
                        )
    #FIXME: Is this necessary or refective of bad design?
    conduit.mappingDB.delete_mapping(
                        sourceUID=sink.get_UID(),
                        dataLUID=dataLUID,
                        sinkUID=source.get_UID()
                        )


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

        #Callback functions that syncworkers call. Saves having to make this
        #inherit from gobject and re-pass all the signals
        self.syncStartedCbs = []
        self.syncCompleteCbs = []
        self.syncConflictCbs = []
        self.syncProgressCbs = []

        #Two way sync policy
        self.policy = {"conflict":"ask","deleted":"ask"}

    def _connect_sync_thread_callbacks(self, thread):
        for cb in self.syncStartedCbs:
            thread.connect("sync-started", cb)
        for cb in self.syncCompleteCbs:
            thread.connect("sync-completed", cb)
        for cb in self.syncConflictCbs:
            thread.connect("sync-conflict", cb)
        for cb in self.syncProgressCbs:
            thread.connect("sync-progress", cb)

        return thread

    def _cancel_sync_thread(self, conduit):
        logw("Conduit already in queue (alive: %s)" % self.syncWorkers[conduit].isAlive())
        #If the thread is alive then cancel it
        if self.syncWorkers[conduit].isAlive():
            logw("Cancelling thread")
            self.syncWorkers[conduit].cancel()
            self.syncWorkers[conduit].join() #Will block

    def add_syncworker_callbacks(self, syncStartedCb, syncCompleteCb, syncConflictCb, syncProgressCb):
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
        if syncProgressCb != None and syncProgressCb not in self.syncProgressCbs:
            self.syncProgressCbs.append(syncProgressCb)

    def set_twoway_policy(self, policy):
        logd("Setting sync policy: %s" % policy)
        self.policy = policy
        #It is NOT threadsafe to apply to existing conduits

    def cancel_all(self):
        """
        Cancels all threads and also joins() them. Will block
        """
        for c in self.syncWorkers:
            self._cancel_sync_thread(c)
             
    def join_all(self, timeout=None):
        """
        Joins all threads. This function will block the calling thread
        """
        for c in self.syncWorkers:
            self.syncWorkers[c].join(timeout)

    def refresh_dataprovider(self, dataprovider):
        if dataprovider in self.syncWorkers:
            self._cancel_sync_thread(dataprovider)

        #Create a new thread over top
        newThread = RefreshWorker(dataprovider)
        self.syncWorkers[conduit] = self._connect_sync_thread_callbacks(newThread)
        self.syncWorkers[conduit].start()

    def refresh_conduit(self, conduit):
        """
            """
        if conduit in self.syncWorkers:
            self._cancel_sync_thread(conduit)

        #Create a new thread over top
        newThread = SyncWorker(self.typeConverter, conduit, False, self.policy)
        self.syncWorkers[conduit] = self._connect_sync_thread_callbacks(newThread)
        self.syncWorkers[conduit].start()

    def sync_conduit(self, conduit):
        """
        @todo: Send some signals back to the GUI to disable clicking
        on the conduit
        """
        if conduit in self.syncWorkers:
            self._cancel_sync_thread(conduit)

        #Create a new thread over top.
        newThread = SyncWorker(self.typeConverter, conduit, True, self.policy)
        self.syncWorkers[conduit] = self._connect_sync_thread_callbacks(newThread)
        self.syncWorkers[conduit].start()

    def sync_aborted(self, conduit):
        """
        Returns True if the supplied conduit aborted (the sync did not complete
        due to an unhandled exception
        """
        try:
            return self.syncWorkers[conduit].aborted
        except KeyError:
            return True

class _ThreadedWorker(threading.Thread, gobject.GObject):
    """
    A GObject that runs in a python thread, signalling to the gui
    via signals when it completes. Base class for refresh and syncronization
    operations
    """

    __gsignals__ =  { 
                    "sync-conflict": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT,      #datasource wrapper
                        gobject.TYPE_PYOBJECT,      #from data
                        gobject.TYPE_PYOBJECT,      #datasink wrapper
                        gobject.TYPE_PYOBJECT,      #to data
                        gobject.TYPE_PYOBJECT,      #valid resolve choices
                        gobject.TYPE_BOOLEAN]),     #Is the conflict from a deletion
                    "sync-completed": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_BOOLEAN]),     #True if there was an error
                    "sync-started": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "sync-progress": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT,      #conduit,
                        gobject.TYPE_FLOAT])        #percent complete
                    }

    def __init__(self):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)

        #Python threads are not cancellable. Hopefully this will be fixed
        #in Python 3000
        self.cancelled = False

        #true if the sync aborts via an unhandled exception
        self.aborted = False

    def cancel(self):
        """
        Cancels the sync thread. Does not do so immediately but as soon as
        possible.
        """
        self.cancelled = True

    def _get_changes(self, source, sink):
        """
        Returns all the data from the source to the sink. If the dataprovider
        implements get_changes() then this is called. Otherwise the dataprovider
        is proxied using DeltaProvider

        @returns: added, modified, deleted
        """
        if hasattr(source.module, "get_changes"):
            added, modified, deleted = source.module.get_changes()
        else:
            delta = DeltaProvider.DeltaProvider(source, sink)
            added, modified, deleted = delta.get_changes()
        return added, modified, deleted

class SyncWorker(_ThreadedWorker):
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

    def __init__(self, typeConverter, conduit, do_sync, policy):
        """
        @param conduit: The conduit to synchronize
        @type conduit: L{conduit.Conduit.Conduit}
        @param typeConverter: The typeconverter
        @type typeConverter: L{conduit.TypeConverter.TypeConverter}
        """
        _ThreadedWorker.__init__(self)
        self.typeConverter = typeConverter
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

    def _transfer_data(self, source, sink, data):
        """
        Transfers the data from source to sink, includes performing any conversions,
        handling exceptions, etc.

        @returns: The data that was put or None
        """
        newdata = None
        try:
            #convert data type if necessary
            newdata = self._convert_data(sink, source.get_out_type(), sink.get_in_type(), data)
            try:
                #Get existing mapping
                LUID = conduit.mappingDB.get_matching_UID(
                                        sourceUID=source.get_UID(),
                                        sourceDataLUID=newdata.get_UID(),
                                        sinkUID=sink.get_UID()
                                        )
                _put_data(source, sink, newdata, LUID, False)
            except Exceptions.SynchronizeConflictError, err:
                comp = err.comparison
                if comp == COMPARISON_OLDER:
                    log("Skipping %s (Older)" % newdata)
                elif comp == COMPARISON_EQUAL:
                    log("Skipping %s (Equal)" % newdata)
                else:
                    self._apply_conflict_policy(source, sink, err.comparison, err.fromData, err.toData)

        except Exceptions.ConversionDoesntExistError:
            logw("ConversionDoesntExistError")
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_SKIPPED
        except Exceptions.ConversionError, err:
            logw("%s\n%s" % (err, traceback.format_exc()))
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
        except Exceptions.SyncronizeError, err:
            logw("%s\n%s" % (err, traceback.format_exc()))                     
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
        except Exceptions.SyncronizeFatalError, err:
            logw("%s\n%s" % (err, traceback.format_exc()))
            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                                  
            source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
            #Cannot continue
            raise Exceptions.StopSync                  
        except Exception:       
            #Cannot continue
            logw("UNKNOWN SYNCHRONIZATION ERROR\n%s" % traceback.format_exc())
            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
            source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
            raise Exceptions.StopSync

        return newdata

    def _apply_deleted_policy(self, sourceWrapper, sourceDataLUID, sinkWrapper, sinkDataLUID):
        """
        Applies user policy when data has been deleted from source.
        sourceDataLUID is the original UID of the data that has been deleted
        sinkDataLUID is the uid of the data in sink that should now be deleted
        """
        if self.policy["deleted"] == "skip":
            logd("Deleted Policy: Skipping")
        elif self.policy["deleted"] == "ask":
            logd("Deleted Policy: Ask")
            #check if the source is visually on the left of the sink
            if self.source == sourceWrapper:
                #it is on the left
                #dont support copying back yet
                #(CONFLICT_COPY_SINK_TO_SOURCE,CONFLICT_SKIP)
                validResolveChoices = (CONFLICT_DELETE, CONFLICT_SKIP) 
            else:
                #dont support copying back yet
                #(CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE)
                validResolveChoices = (CONFLICT_DELETE, CONFLICT_SKIP) 
            gobject.idle_add(self.emit,"sync-conflict", 
                        sourceWrapper,              #datasource wrapper
                        DeletedData(sourceDataLUID),#from data
                        sinkWrapper,                #datasink wrapper
                        DeletedData(sinkDataLUID),  #to data
                        validResolveChoices,        #valid resolve choices
                        True                        #This conflict is a deletion
                        )
        elif self.policy["deleted"] == "replace":
            _delete_data(sourceWrapper, sinkWrapper, sinkDataLUID)
         
    def _apply_conflict_policy(self, sourceWrapper, sinkWrapper, comparison, fromData, toData):
        """
        Applies user policy when a put() has failed. This may mean emitting
        the conflict up to the GUI or skipping altogether
        """
        if comparison == COMPARISON_EQUAL or comparison == COMPARISON_UNKNOWN or comparison == COMPARISON_OLDER:
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            if self.policy["conflict"] == "skip":
                logd("Conflict Policy: Skipping")
            elif self.policy["conflict"] == "ask":
                logd("Conflict Policy: Ask")
                if sourceWrapper.module_type in ["twoway", "sink"]:
                    #in twoway case the user can copy back
                    avail = (CONFLICT_SKIP,CONFLICT_COPY_SOURCE_TO_SINK,CONFLICT_COPY_SINK_TO_SOURCE)
                else:
                    avail = (CONFLICT_SKIP,CONFLICT_COPY_SOURCE_TO_SINK)

                gobject.idle_add(self.emit,"sync-conflict", 
                            sourceWrapper, 
                            fromData, 
                            sinkWrapper, 
                            toData, 
                            avail,
                            False
                            )
            elif self.policy["conflict"] == "replace":
                logd("Conflict Policy: Replace")
                try:
                    LUID = conduit.mappingDB.get_matching_UID(
                                            sourceUID=sourceWrapper.get_UID(),
                                            sourceDataLUID=toData.get_UID(),
                                            sinkUID=sinkWrapper.get_UID()
                                            )
                    _put_data(sourceWrapper, sinkWrapper, toData, LUID, True)
                except:
                    logw("Forced Put Failed\n%s" % traceback.format_exc())        
        #This should not happen...
        else:
            logw("UNKNOWN COMPARISON\n%s" % traceback.format_exc())
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT

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

    def one_way_sync(self, source, sink):
        """
        Transfers numItems of data from source to sink.
        """
        log("Synchronizing %s |--> %s " % (source, sink))

        #get all the data
        added, modified, deleted = self._get_changes(source, sink)

        #handle deleted data
        for d in deleted:
            matchingUID = conduit.mappingDB.get_matching_UID(source.get_UID(), d, sink.get_UID())
            if matchingUID != None:
                self._apply_deleted_policy(source, d, sink, matchingUID)

        #one way sync treats added and modifed the same. Both get transferred
        items = added + modified
        numItems = len(items)
        idx = 0
        for i in items:
            idx += 1.0
            self.check_thread_not_cancelled([source, sink])

            data = source.module.get(i)
            logd("1WAY PUT: %s (%s) -----> %s" % (source.name,data.get_UID(),sink.name))

            #work out the percent complete
            done = idx/(numItems*len(self.sinks)) + \
                    float(self.sinks.index(sink))/len(self.sinks)
            gobject.idle_add(self.emit, "sync-progress", self.conduit, done)

            #transfer the data
            newdata = self._transfer_data(source, sink, data)
       
    def two_way_sync(self, source, sink):
        """
        Performs a two way sync from source to sink and back.
        """
        log("Synchronizing (Two Way) %s <--> %s " % (source, sink))
        #Need to do all the analysis before we touch the mapping db
        toput = []      # (sourcedp, dataUID, sinkdp)
        todelete = []   # (sourcedp, dataUID, sinkdp)
        tocomp = []     # (dp1, data1UID, dp2, data2UID)

        #PHASE ONE: CALCULATE WHAT NEEDS TO BE DONE
        #get all the datauids
        sourceAdded, sourceModified, sourceDeleted = self._get_changes(source, sink)
        sinkAdded, sinkModified, sinkDeleted = self._get_changes(sink, source)

        #added data can be put right away
        toput += [(source, i, sink) for i in sourceAdded]
        toput += [(sink, i, source) for i in sinkAdded]

        def modified_and_deleted(dp1, modified, dp2, deleted):
            found = []
            for i in modified[:]:
                matchingUID = conduit.mappingDB.get_matching_UID(dp1.get_UID(), i, dp2.get_UID())
                logd("%s, %s" % (i, matchingUID))
                if deleted.count(matchingUID) != 0:
                    logd("MOD+DEL: %s v %s" % (i, matchingUID))
                    deleted.remove(matchingUID)
                    modified.remove(i)
                    found += [(dp2, matchingUID, dp1)]
            return found

        todelete += modified_and_deleted(source, sourceModified, sink, sinkDeleted)
        todelete += modified_and_deleted(sink, sinkModified, source, sourceDeleted)

        #as can deleted data
        todelete += [(source, i, sink) for i in sourceDeleted]
        todelete += [(sink, i, source) for i in sinkDeleted]

        #modified is a bit harder because we need to check if both side have
        #been modified at the same time. First find items in both lists and seperate
        #them out as they need to be compared.
        for i in sourceModified[:]:
            matchingUID = conduit.mappingDB.get_matching_UID(source.get_UID(), i, sink.get_UID())
            if sinkModified.count(matchingUID) != 0:
                logw("BOTH MODIFIED: %s v %s" % (i, matchingUID))
                sourceModified.remove(i)
                sinkModified.remove(matchingUID)
                tocomp.append( (source, i, sink, matchingUID) )

        #all that remains in the original lists are to be put
        toput += [(source, i, sink) for i in sourceModified]
        toput += [(sink, i, source) for i in sinkModified]

        #PHASE TWO: TRANSFER DATA
        for sourcedp, dataUID, sinkdp in todelete:
            matchingUID = conduit.mappingDB.get_matching_UID(sourcedp.get_UID(), dataUID, sinkdp.get_UID())
            logd("2WAY DEL: %s (%s)" % (sinkdp.name, matchingUID))
            if matchingUID != None:
                self._apply_deleted_policy(sourcedp, dataUID, sinkdp, matchingUID)

        for sourcedp, dataUID, sinkdp in toput:
            data = sourcedp.module.get(dataUID)
            logd("2WAY PUT: %s (%s) -----> %s" % (sourcedp.name,dataUID,sinkdp.name))
            self._transfer_data(sourcedp, sinkdp, data)

        for dp1, data1UID, dp2, data2UID in tocomp:
            logd("2WAY CMP: %s (%s) <----> %s (%s)" % (dp1.name,data1UID,dp2.name,data2UID))
            data1 = dp1.module.get(data1UID)
            data2 = dp2.module.get(data2UID)
            d1mtime = data1.get_mtime()
            d2mtime = data2.get_mtime()
            if d1mtime == None and d2mtime == None:
                self._apply_conflict_policy(dp1, dp2, COMPARISON_UNKNOWN, data1, data2)
            else:
                if d1mtime > d2mtime:
                    sourcedp = dp1
                    sinkdp = dp2
                    fromdata = data2
                    todata = data1
                else:
                    sourcedp = dp2
                    sinkdp = dp1
                    fromdata = data1
                    todata = data2

                self._apply_conflict_policy(sourcedp, sinkdp, COMPARISON_UNKNOWN, fromdata, todata)

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
        try:
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
            gobject.idle_add(self.emit, "sync-started")
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
                        logw("Not enough configured datasinks")
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
                        logw("RefreshError: %s" % self.source)
                        #Cannot continue with no source data
                        raise Exceptions.StopSync
                    except Exception, err:
                        self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                        logw("UNKNOWN REFRESH ERROR: %s\n%s" % (self.source,traceback.format_exc()))
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
                                logw("RefreshError: %s" % sink)
                                sinkDidntRefreshOK[sink] = True
                                self.sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                            except Exception:
                                logw("UNKNOWN REFRESH ERROR: %s\n%s" % (sink,traceback.format_exc()))
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
                        log("Not enough sinks refreshed")
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
                                self.one_way_sync(self.source, sink)
     
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

        except Exceptions.StopSync:
            logw("Sync Aborted")
            self.aborted = True

        conduit.mappingDB.save()
        gobject.idle_add(self.emit, "sync-completed", self.aborted or len(self.sinkErrors) != 0)

class RefreshWorker(_ThreadedWorker):
    """
    Refreshes a single dataprovider, handling any errors, etc
    """

    def __init__(self, dataproviderWrapper):
        """
        @param dataproviderWrapper: The dp to refresh
        """
        _ThreadedWorker.__init__(self)
        self.dataproviderWrapper = dataproviderWrapper

        self.setName("%s" % self.dataproviderWrapper)

    def run(self):
        """
        The main refresh state machine.
        
        Takes the conduit through the init->is_configured->refresh
        steps, setting its status at the appropriate time and performing
        nicely in the case of errors. 
        """
        try:
            logd("Refresh %s beginning" % self)
            gobject.idle_add(self.emit, "sync-started")


            if not self.dataproviderWrapper.module.is_configured():
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_SYNC_NOT_CONFIGURED)
                #Cannot continue if source not configured
                raise Exceptions.StopSync
        
            try:
                self.dataproviderWrapper.module.refresh()
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
            except Exceptions.RefreshError:
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                logw("RefreshError: %s" % self.dataproviderWrapper)
                #Cannot continue with no source data
                raise Exceptions.StopSync
            except Exception, err:
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                logw("UNKNOWN REFRESH ERROR: %s\n%s" % (self.dataproviderWrapper,traceback.format_exc()))
                #Cannot continue with no source data
                raise Exceptions.StopSync           

        except Exceptions.StopSync:
            logw("Sync Aborted")
            self.aborted = True

        conduit.mappingDB.save()
        gobject.idle_add(self.emit, "sync-completed", self.aborted)

                
class DeletedData(DataType.DataType):
    """
    Simple wrapper around a deleted item. If an item has been deleted then
    we can no longer rely on its open_URI, and we must fall back to a 
    plain string object
    """
    def __init__(self, UID, **kwargs):
        self.UID = UID
        self.snippet = kwargs.get("snippet", "Deleted %s" % self.UID)

    def get_UID(self):
        return self.UID
        
    def get_snippet(self):
        return self.snippet

    def get_open_URI(self):
        return None

    def __str__(self):
        return "Deleted Data: %s" % self.UID
