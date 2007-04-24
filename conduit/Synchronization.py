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
        newThread = SyncWorker(self.typeConverter, conduit, False, self.policy)
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
        newThread = SyncWorker(self.typeConverter, conduit, True, self.policy)
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
                    "sync-conflict": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT,      #datasource wrapper
                        gobject.TYPE_PYOBJECT,      #from data
                        gobject.TYPE_PYOBJECT,      #datasink wrapper
                        gobject.TYPE_PYOBJECT,      #to data
                        gobject.TYPE_PYOBJECT,      #valid resolve choices
                        gobject.TYPE_BOOLEAN]),     #Is the conflict from a deletion
                    "sync-completed": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "sync-started": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
                    "sync-progress": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT,      #conduit,
                        gobject.TYPE_FLOAT])        #percent complete
                    }

    def __init__(self, typeConverter, conduit, do_sync, policy):
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

    def _put_data(self, source, sink, data, LUID, mtime, overwrite):
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
                                sinkUID=sink.get_UID(),
                                sinkDataLUID=LUID,
                                mtime=mtime
                                )

    def _delete_data(self, source, sink, dataLUID):
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

    def _transfer_data(self, source, sink, data):
        """
        Transfers the data from source to sink, includes performing any conversions,
        handling exceptions, etc. Only transfers data if the mtime of the
        data has changed

        @returns: The data that was put or None
        """
        newdata = None
        try:
            #convert data type if necessary
            newdata = self._convert_data(sink, source.get_out_type(), sink.get_in_type(), data)
            try:
                #Get existing mapping
                LUID, mtime = conduit.mappingDB.get_mapping(
                                        sourceUID=source.get_UID(),
                                        sourceDataLUID=newdata.get_UID(),
                                        sinkUID=sink.get_UID()
                                        )
                if newdata.get_mtime() != mtime or self.conduit.do_slow_sync():
                    self._put_data(source, sink, newdata, LUID, mtime, False)
                else:
                    log("Skipping %s. Mtimes has not changed (actual %s v saved %s)" % (newdata.get_UID(), newdata.get_mtime(), mtime))
            except Exceptions.SynchronizeConflictError, err:
                comp = err.comparison
                if comp == COMPARISON_OLDER:
                    log("Skipping %s (Older)" % newdata)
                elif comp == COMPARISON_EQUAL:
                    log("Skipping %s (Equal)" % newdata)
                else:
                    self._apply_conflict_policy(source, sink, err.comparison, err.fromData, err.toData)

        except Exceptions.ConversionDoesntExistError:
            logw("No Conversion Exists")
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_SKIPPED
        except Exceptions.ConversionError, err:
            logw("Error converting %s\n%s" % (err, traceback.format_exc()))
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
        except Exceptions.SyncronizeError, err:
            logw("Error synchronizing %s\n%s" % (err, traceback.format_exc()))                     
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
        except Exceptions.SyncronizeFatalError, err:
            logw("Error synchronizing %s\n%s" % (err, traceback.format_exc()))
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

        return newdata

    def _apply_deleted_policy(self, sourceWrapper, sinkWrapper, dataLUID):
        """
        Applies user policy when data has been deleted from source.

        Depending on if the dp is on the left or not, the arrows may suggest
        resolution in different directions
        """
        if self.policy["deleted"] == "skip":
            logd("Deleted Policy: Skipping")
        elif self.policy["deleted"] == "ask":
            logd("Deleted Policy: Ask")
            #check if the source is visually on the left of the sink
            if self.source == sourceWrapper:
                #it is on the left
                validResolveChoices = (CONFLICT_COPY_SINK_TO_SOURCE,CONFLICT_SKIP)
            else:
                validResolveChoices = (CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE)
            gobject.idle_add(self.emit,"sync-conflict", 
                        sourceWrapper,              #datasource wrapper
                        DeletedData(dataLUID),      #from data
                        sinkWrapper,                #datasink wrapper
                        DeletedData(None),          #to data
                        validResolveChoices,        #valid resolve choices
                        True                        #This conflict is a deletion
                        )
        elif self.policy["deleted"] == "replace":
            self._delete_data(sourceWrapper, sinkWrapper, dataLUID)
         
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
                gobject.idle_add(self.emit,"sync-conflict", 
                            sourceWrapper, 
                            fromData, 
                            sinkWrapper, 
                            toData, 
                            (CONFLICT_COPY_SOURCE_TO_SINK,CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE),
                            False
                            )
            elif self.policy["conflict"] == "replace":
                logd("Conflict Policy: Replace")
                try:
                    LUID, mtime = conduit.mappingDB.get_mapping(
                                            sourceUID=sourceWrapper.get_UID(),
                                            sourceDataLUID=toData.get_UID(),
                                            sinkUID=sinkWrapper.get_UID()
                                            )
                    self._put_data(sourceWrapper, sinkWrapper, toData, LUID, mtime, True)
                except:
                    logw("Forced Put Failed\n%s" % traceback.format_exc())        
        #This should not happen...
        else:
            logw("Unknown comparison\n%s" % traceback.format_exc())
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

    def one_way_sync(self, source, sink):
        """
        Transfers numItems of data from source to sink.
        """
        log("Synchronizing %s |--> %s " % (source, sink))

        numItems = source.module.get_num_items()
        #Detecting items which have been deleted involves comparing the
        #data LUIDs which are returned from the get() with those 
        #that were synchronized last time
        existing = [i["sourceDataLUID"] for i in conduit.mappingDB.get_mappings_for_dataproviders(source.get_UID(), sink.get_UID())]

        for i in range(0, numItems):
            self.check_thread_not_cancelled([source, sink])

            data = source.module.get(i)
            logd("1WAY PUT: %s (%s) -----> %s" % (source.name,data.get_UID(),sink.name))

            #work out the percent complete
            done = (i+1.0)/(numItems*len(self.sinks)) + \
                    float(self.sinks.index(sink))/len(self.sinks)
            gobject.idle_add(self.emit, "sync-progress", self.conduit, done)

            newdata = self._transfer_data(source, sink, data)
            #now remove from the list of expected data to synchronize
            if existing.count(newdata.get_UID()):
                existing.remove(newdata.get_UID())

        #give dataproviders the freedom to also provide a list of deleted 
        #data UIDs.
        deleted = Utils.distinct_list(existing + source.module.get_deleted_items())
        logd("There were %s deleted items" % len(deleted))
        for d in deleted:
            self._apply_deleted_policy(source, sink, d)
       
    def two_way_sync(self, source, sink):
        """
        Performs a two way sync from source to sink and back.
        General approach
            1.  Get all the data from both DPs
            2.  Get all existing relationships
            3.  Go through all the data and classify into the following
                a.  Data with no existing mappings.  This is basically new
                    data so can be put into the corresponding sink
                b.  Data for which a mapping exists. This can then be classified
                    into 
                    1.  The mtime of the data has not changed at either end. Skip
                    2.  The mtime of the data has changed. Compare the data to 
                        see which is newer
                    3.  Data that is missing from the existing mappings, i.e. data
                        that has been deleted
        """
        log("Synchronizing (Two Way) %s <--> %s " % (source, sink))
        sourceData = [source.module.get(i) for i in range(0,source.module.get_num_items())]
        sinkData = [sink.module.get(i) for i in range(0,sink.module.get_num_items())]
        
        known = {}
        #first look up the existing relationships
        # key = [UID]
        # values = (mtime, correspondingDataUID, correspondingOtherDataproviderUID)
        for i in conduit.mappingDB.get_mappings_for_dataproviders(source.get_UID(), sink.get_UID()):
            if known.has_key(i["sourceDataLUID"]) or known.has_key(i["sinkDataLUID"]):
                pass
            else:
                known[ i["sourceDataLUID"] ] = (i["mtime"],i["sinkDataLUID"],i["sourceUID"])
                known[ i["sinkDataLUID"] ] = (i["mtime"],i["sourceDataLUID"],i["sinkUID"])

        #precompute the actions. mostly for debugability
        #PHASE ONE
        toput = []      # (sourcedp, data, sinkdp)
        tocomp = []     # (dp1, data1, dp2, data2, mtime)
        todelete = []   # (sourcedp, dataUID, sinkdp)
        #the difficulty is that if some data is known then we need to wait for
        #its matching pair before we can compare it and decide who is newer
        waitingForData = {}
        # key: the UID of the data we are waiting for
        # value: the data, dp and mtime we know
        #messy list foo...... but need to do this both ways smartly
        for sourcedp,sinkdp in [ (source,sink), (sink,source) ]:
            for data in [sourcedp.module.get(i) for i in range(0, sourcedp.module.get_num_items())]:
                dataUID = data.get_UID()
                logd("2WAY DAT: %s" % dataUID)
                #are we waiting for this data
                if waitingForData.has_key(dataUID):
                    olddp, olddata, olduid, mtime = waitingForData[dataUID]
                    if olddata.get_mtime() != mtime or data.get_mtime() != mtime or self.conduit.do_slow_sync():
                        # CASE 3.b.2
                        tocomp.append( (olddp, olddata, sourcedp, data, mtime) )
                    else:
                        # CASE 3.b.1
                        logd("Skipping %s and %s. Mtimes has not changed (%s)" % (olddata.get_UID(), data.get_UID(), mtime))
                    del(known[dataUID])
                else:
                    if known.has_key(dataUID):
                        mtime, matchingUID, sourceUID = known[dataUID]
                        #its a known relationship so wait for its friend
                        waitingForData[matchingUID] = (sourcedp, data, dataUID, mtime)
                        del(known[dataUID])
                    else:
                        # CASE 3.a
                        toput.append( (sourcedp, data, sinkdp) )

            #no go and see what data remains that was previously known about, and that
            #has now been deleted from the sink
            for k in known:
                mtime, matchingUID, sourceUID = known[k]
                if sourcedp.get_UID() == sourceUID:
                    # CASE 3.b.3
                    logd("DELETED %s from %s. Remove %s from %s" % (k, sourcedp.name, matchingUID, sinkdp.name))
                    todelete.append( (sourcedp, matchingUID, sinkdp) )
    
        #PHASE TWO
        for sourcedp, data, sinkdp in toput:
            logd("2WAY PUT: %s (%s) -----> %s" % (sourcedp.name,data.get_UID(),sinkdp.name))
            self._transfer_data(sourcedp, sinkdp, data)

        for dp1, data1, dp2, data2, mtime in tocomp:
            logd("2WAY CMP: %s (%s) <----> %s (%s)" % (dp1.name,data1.get_UID(),dp2.name,data2.get_UID()))
            #Convert from the most modified data into the other. Remember that items are 
            #only in this list if their mtimes have changed. 
            #three cases
            #A) mtimes are both None - user decides which is newer
            #B) both mtimes have changed - compare method
            #C) one mtime has changed - transfer data
            d1mtime = data1.get_mtime()
            d2mtime = data2.get_mtime()
            if d1mtime == None and d2mtime == None:
                #case A
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

                if d1mtime != mtime and d2mtime != mtime:
                    #case B
                    #FIXME: Convert and compare
                    self._apply_conflict_policy(sourcedp, sinkdp, COMPARISON_UNKNOWN, fromdata, todata)
                else:
                    #case C
                    self._transfer_data(sourcedp, sinkdp, fromdata)

        for sourcedp, uid, sinkdp in todelete:
            logd("2WAY DEL: %s (%s)" % (sinkdp.name, uid))
            self._apply_deleted_policy(sourcedp, sinkdp, uid)

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

        conduit.mappingDB.save()
        gobject.idle_add(self.emit, "sync-completed")
                
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
