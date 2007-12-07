"""
Holds class used for the actual synchronisation phase

Copyright: John Stowers, 2006
License: GPLv2
"""

import traceback
import threading
import logging
log = logging.getLogger("Syncronization")


import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.DeltaProvider as DeltaProvider

from conduit.Conflict import Conflict, CONFLICT_DELETE, CONFLICT_COPY_SOURCE_TO_SINK,CONFLICT_SKIP,CONFLICT_COPY_SINK_TO_SOURCE
from conduit.datatypes import DataType, Rid, COMPARISON_OLDER, COMPARISON_EQUAL, COMPARISON_NEWER, COMPARISON_UNKNOWN

def put_data(source, sink, sourceData, sourceDataRid, overwrite):
    """
    Puts sourceData into sink, overwrites if overwrite is True. Updates 
    the mappingDB
    """
    #get the existing mapping
    mapping = conduit.GLOBALS.mappingDB.get_mapping(
                            sourceUID=source.get_UID(),
                            dataLUID=sourceDataRid.get_UID(),
                            sinkUID=sink.get_UID()
                            )
    sourceDataLUID = sourceDataRid.get_UID()
    sinkDataLUID = mapping.get_sink_rid().get_UID()

    #put the data
    log.info("Putting data %s --> %s into %s" % (sourceDataLUID, sinkDataLUID, sink.get_UID()))
    sinkRid = sink.module.put(
                    sourceData, 
                    overwrite, 
                    sinkDataLUID)
    
    #Update the mapping and save
    mapping.set_source_rid(sourceDataRid)
    mapping.set_sink_rid(sinkRid)
    conduit.GLOBALS.mappingDB.save_mapping(mapping)

def delete_data(source, sink, dataLUID):
    """
    Deletes data from sink and updates the mapping DB
    """
    log.info("Deleting %s from %s" % (dataLUID, sink.get_UID()))
    sink.module.delete(dataLUID)
    mapping = conduit.GLOBALS.mappingDB.get_mapping(
                        sourceUID=source.get_UID(),
                        dataLUID=dataLUID,
                        sinkUID=sink.get_UID()
                        )
    conduit.GLOBALS.mappingDB.delete_mapping(mapping)

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

        #Two way sync policy
        self.policy = {"conflict":"skip","deleted":"skip"}

    def _cancel_sync_thread(self, cond):
        log.warn("Conduit already in queue (alive: %s)" % self.syncWorkers[cond].isAlive())
        #If the thread is alive then cancel it
        if self.syncWorkers[cond].isAlive():
            log.warn("Cancelling thread")
            self.syncWorkers[cond].cancel()
            self.syncWorkers[cond].join() #Will block

    def _on_sync_completed(self, cond, abort, error, conflict, worker):
        if cond in self.syncWorkers:
            log.debug("Deleting worker: %s" % worker)
            del(self.syncWorkers[cond])

    def _start_worker_thread(self, cond, worker):
        log.debug("Starting worker: %s" % worker)
        cond.connect("sync-completed", self._on_sync_completed, worker)
        self.syncWorkers[cond] = worker
        self.syncWorkers[cond].start()

    def sync_in_progress(self, cond):
        """
        Returns true if cond is currently undergoing sync, refresh etc
        """
        return cond in self.syncWorkers

    def set_twoway_policy(self, policy):
        """
        FIXME: Should be a per conduit setting
        """
        log.debug("Setting sync policy: %s" % policy)
        self.policy = policy

    def cancel_all(self):
        """
        Cancels all threads and also joins() them. Will block
        """
        for c in self.syncWorkers:
            self._cancel_sync_thread(c)

    def join_one(self, cond, timeout=None):
        """
        Blocks until the thread associated with the supplied conduit finishes
        """
        log.info("Waiting for thread to finish")
        self.syncWorkers[cond].join(timeout)

    def join_all(self, timeout=None):
        """
        Joins all threads. This function will block the calling thread
        """
        for c in self.syncWorkers:
            self.syncWorkers[c].join(timeout)

    def refresh_dataprovider(self, cond, dataprovider):
        if cond in self.syncWorkers:
            log.info("Refresh dataprovider already in progress")
            self.join_one(cond)            

        threadedWorker = RefreshDataProviderWorker(cond, dataprovider)
        self._start_worker_thread(cond, threadedWorker)

    def refresh_conduit(self, cond):
        if cond in self.syncWorkers:
            log.info("Refresh already in progress")
            self.join_one(cond)

        threadedWorker = SyncWorker(self.typeConverter, cond, False, self.policy)
        self._start_worker_thread(cond, threadedWorker)

    def sync_conduit(self, cond):
        if cond in self.syncWorkers:
            log.info("Sync already in progress")
            self.join_one(cond)

        threadedWorker = SyncWorker(self.typeConverter, cond, True, self.policy)
        self._start_worker_thread(cond, threadedWorker)

    def did_sync_abort(self, cond):
        """
        Returns True if the supplied conduit aborted (the sync did not complete
        due to an unhandled exception, a SynchronizeFatalError or the conduit was
        unsyncable (source did not refresh, etc)
        """
        return self.syncWorkers[cond].aborted

    def did_sync_error(self, cond):
        """
        Returns True if the supplied conduit raised a non fatal 
        SynchronizeError during sync
        """
        return self.syncWorkers[cond].did_sync_error()

    def did_sync_conflict(self, cond):
        """
        Returns True if the supplied conduit encountered a conflict during processing
        """
        return self.syncWorkers[cond].did_sync_conflict()
        
class _ThreadedWorker(threading.Thread):
    """
    Aa python thread, Base class for refresh and syncronization
    operations
    """
    def __init__(self):
        threading.Thread.__init__(self)

        #Python threads are not cancellable. Hopefully this will be fixed
        #in Python 3000
        self.cancelled = False

        #true if the sync aborts via an unhandled exception
        self.aborted = False
        #Keep track of any non conflicts, fatal errors (or trapped exceptions) in the sync process. 
        #Class variable because these may occur in a data conversion. 
        #Needed so that the correct status is shown on the GUI at the end of the sync process
        self.sinkErrors = {}
        
    def _get_changes(self, source, sink):
        """
        Returns all the data from the source to the sink. If the dataprovider
        implements get_changes() then this is called. Otherwise the dataprovider
        is proxied using DeltaProvider

        @returns: added, modified, deleted
        """
        try:
            added, modified, deleted = source.module.get_changes()
        except NotImplementedError:
            delta = DeltaProvider.DeltaProvider(source, sink)
            added, modified, deleted = delta.get_changes()

        log.debug("%s Changes: New %s items\n%s" % (source.get_UID(), len(added), added))
        log.debug("%s Changes: Modified %s items\n%s" % (source.get_UID(), len(modified), modified))
        log.debug("%s Changes: Deleted %s items\n%s" % (source.get_UID(), len(deleted), deleted))

        #FIXME: Copy the lists because they are modified in place somewhere...
        return added[:], modified[:], deleted[:]

    def cancel(self):
        """
        Cancels the sync thread. Does not do so immediately but as soon as
        possible.
        """
        self.cancelled = True
        
    def did_sync_error(self):
        #conflicts do not specifically count as errors so remove them
        errors = self.sinkErrors.values()
        while True:
            try: errors.remove(DataProvider.STATUS_DONE_SYNC_CONFLICT)
            except ValueError: break
        return len(errors) > 0

    def did_sync_conflict(self):
        errors = self.sinkErrors.values()
        return DataProvider.STATUS_DONE_SYNC_CONFLICT in errors

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

    def __init__(self, typeConverter, cond, do_sync, policy):
        _ThreadedWorker.__init__(self)
        self.typeConverter = typeConverter
        self.cond = cond
        self.source = cond.datasource
        self.sinks = cond.datasinks
        self.do_sync = do_sync
        self.policy = policy

        #Start at the beginning
        self.state = SyncWorker.CONFIGURE_STATE

        if self.cond.is_two_way():
            self.setName("%s <--> %s" % (self.source, self.sinks[0]))
        else:
            self.setName("%s |--> %s" % (self.source, self.sinks))

    def _get_data(self, source, sink, uid):
        """
        Gets the data from source. Handles exceptions, etc.

        @returns: The data that was got or None
        """
        data = None
        try:
            data = source.module.get(uid)
        except Exceptions.SyncronizeError, err:
            log.warn("%s\n%s" % (err, traceback.format_exc()))                     
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
            log.debug("ERROR GETTING DATA")
        except Exceptions.SyncronizeFatalError, err:
            log.warn("%s\n%s" % (err, traceback.format_exc()))
            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                                  
            source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
            #Cannot continue
            raise Exceptions.StopSync                  
        except Exception:       
            #Cannot continue
            log.critical("UNKNOWN SYNCHRONIZATION ERROR\n%s" % traceback.format_exc())
            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
            source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
            raise Exceptions.StopSync

        return data

    def _put_data(self, source, sink, sourceData, sourceDataRid):
        """
        Handles exceptions when putting data from source to sink. Default is
        not to overwrite
        """
        if sourceData != None:
            try:
                put_data(source, sink, sourceData, sourceDataRid, False)
            except Exceptions.SynchronizeConflictError, err:
                comp = err.comparison
                if comp == COMPARISON_OLDER:
                    log.info("Skipping %s (Older)" % sourceData)
                elif comp == COMPARISON_EQUAL:
                    log.info("Skipping %s (Equal)" % sourceData)
                else:
                    assert(err.fromData == sourceData)
                    self._apply_conflict_policy(source, sink, err.comparison, sourceData, sourceDataRid, err.toData, err.toData.get_rid())
        else:
            log.info("Could not put data: Was None")

    def _convert_data(self, source, sink, data):
        """
        Converts data into a format acceptable for sink, handling exceptions, etc.
        """
        newdata = None
        try:
            newdata = self.typeConverter.convert(source.get_output_type(), sink.get_input_type(), data)
        except Exceptions.ConversionDoesntExistError:
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_SKIPPED
        except Exceptions.ConversionError, err:
            log.warn("Error performing conversion:\n%s" % (err, traceback.format_exc()))
            self.sinkErrors[sink] = DataProvider.STATUS_DONE_SYNC_ERROR
        except Exception:       
            log.critical("UNKNOWN CONVERSION ERROR\n%s" % traceback.format_exc())
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
            log.debug("Deleted Policy: Skipping")
        elif self.policy["deleted"] == "ask":
            log.debug("Deleted Policy: Ask")

            #FIXME: Delete should be handled differently from conflict
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT

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
            
            sourceData = DeletedData(sourceDataLUID)
            sinkData = DeletedData(sinkDataLUID)
            c = Conflict(
                    sourceWrapper,              #datasource wrapper
                    sourceData,                 #from data
                    sourceData.get_rid(),       #from data rid
                    sinkWrapper,                #datasink wrapper
                    sinkData,                   #to data
                    sinkData.get_rid(),         #to data rid
                    validResolveChoices,        #valid resolve choices
                    True                        #This conflict is a deletion
                    )
            self.cond.emit("sync-conflict", c)

        elif self.policy["deleted"] == "replace":
            log.debug("Deleted Policy: Delete")
            #FIXME: Delete should be handled differently from conflict
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT
            delete_data(sourceWrapper, sinkWrapper, sinkDataLUID)
         
    def _apply_conflict_policy(self, sourceWrapper, sinkWrapper, comparison, fromData, fromDataRid, toData, toDataRid):
        """
        Applies user policy when a put() has failed. This may mean emitting
        the conflict up to the GUI or skipping altogether
        """
        if comparison == COMPARISON_EQUAL or comparison == COMPARISON_UNKNOWN or comparison == COMPARISON_OLDER:
            if self.policy["conflict"] == "skip":
                log.debug("Conflict Policy: Skipping")
            elif self.policy["conflict"] == "ask":
                log.debug("Conflict Policy: Ask")
                self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT

                if sourceWrapper.module_type in ["twoway", "sink"]:
                    #in twoway case the user can copy back
                    avail = (CONFLICT_SKIP,CONFLICT_COPY_SOURCE_TO_SINK,CONFLICT_COPY_SINK_TO_SOURCE)
                else:
                    avail = (CONFLICT_SKIP,CONFLICT_COPY_SOURCE_TO_SINK)

                c = Conflict(
                        sourceWrapper, 
                        fromData,
                        fromDataRid, 
                        sinkWrapper, 
                        toData,
                        toDataRid,
                        avail,
                        False
                        )
                self.cond.emit("sync-conflict", c)

            elif self.policy["conflict"] == "replace":
                log.debug("Conflict Policy: Replace")
                self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_CONFLICT

                try:
                    put_data(sourceWrapper, sinkWrapper, fromData, fromDataRid, True)
                except:
                    log.warn("Forced Put Failed\n%s" % traceback.format_exc())        
        #This should not happen...
        else:
            log.warn("UNKNOWN COMPARISON\n%s" % traceback.format_exc())
            self.sinkErrors[sinkWrapper] = DataProvider.STATUS_DONE_SYNC_ERROR

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
        log.info("Synchronizing %s |--> %s " % (source, sink))

        #get all the data
        added, modified, deleted = self._get_changes(source, sink)

        #handle deleted data
        for d in deleted:
            matchingUID = conduit.GLOBALS.mappingDB.get_matching_UID(source.get_UID(), d, sink.get_UID())
            if matchingUID != None:
                self._apply_deleted_policy(source, d, sink, matchingUID)

        #one way sync treats added and modifed the same. Both get transferred
        items = added + modified
        numItems = len(items)
        idx = 0
        for i in items:
            idx += 1.0
            self.check_thread_not_cancelled([source, sink])

            #work out the percent complete
            done = idx/(numItems*len(self.sinks)) + \
                    float(self.sinks.index(sink))/len(self.sinks)
            self.cond.emit("sync-progress", done)

            #transfer the data
            data = self._get_data(source, sink, i)
            if data != None:
                log.debug("1WAY PUT: %s (%s) -----> %s" % (source.name,data.get_UID(),sink.name))
                dataRid = data.get_rid()
                data = self._convert_data(source, sink, data)
                self._put_data(source, sink, data, dataRid)
       
    def two_way_sync(self, source, sink):
        """
        Performs a two way sync from source to sink and back.
        """
        def modified_and_deleted(dp1, modified, dp2, deleted):
            found = []
            for i in modified[:]:
                matchingUID = conduit.GLOBALS.mappingDB.get_matching_UID(dp1.get_UID(), i, dp2.get_UID())
                if deleted.count(matchingUID) != 0:
                    log.debug("2WAY MOD+DEL: %s v %s" % (i, matchingUID))
                    deleted.remove(matchingUID)
                    modified.remove(i)
                    found += [(dp2, matchingUID, dp1)]
            return found
            
        log.info("Synchronizing (Two Way) %s <--> %s " % (source, sink))
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

        #check first for data that had been simulatainously modified and deleted
        todelete += modified_and_deleted(source, sourceModified, sink, sinkDeleted)
        todelete += modified_and_deleted(sink, sinkModified, source, sourceDeleted)

        #as can deleted data
        todelete += [(source, i, sink) for i in sourceDeleted]
        todelete += [(sink, i, source) for i in sinkDeleted]

        #modified is a bit harder because we need to check if both side have
        #been modified at the same time. First find items in both lists and seperate
        #them out as they need to be compared.
        for i in sourceModified[:]:
            matchingUID = conduit.GLOBALS.mappingDB.get_matching_UID(source.get_UID(), i, sink.get_UID())
            if sinkModified.count(matchingUID) != 0:
                log.warn("2WAY BOTH MODIFIED: %s v %s" % (i, matchingUID))
                sourceModified.remove(i)
                sinkModified.remove(matchingUID)
                tocomp.append( (source, i, sink, matchingUID) )

        #all that remains in the original lists are to be put
        toput += [(source, i, sink) for i in sourceModified]
        toput += [(sink, i, source) for i in sinkModified]

        total = len(toput) + len(todelete) + len(tocomp)
        cnt = 0

        #PHASE TWO: TRANSFER DATA
        for sourcedp, dataUID, sinkdp in todelete:
            matchingUID = conduit.GLOBALS.mappingDB.get_matching_UID(sourcedp.get_UID(), dataUID, sinkdp.get_UID())
            log.debug("2WAY DEL: %s (%s)" % (sinkdp.name, matchingUID))
            if matchingUID != None:
                self._apply_deleted_policy(sourcedp, dataUID, sinkdp, matchingUID)

            #progress
            cnt = cnt+1
            self.cond.emit("sync-progress", float(cnt)/total)

        for sourcedp, dataUID, sinkdp in toput:
            data = self._get_data(sourcedp, sinkdp, dataUID)
            if data != None:
                log.debug("2WAY PUT: %s (%s) -----> %s" % (sourcedp.name,dataUID,sinkdp.name))
                dataRid = data.get_rid()
                data = self._convert_data(sourcedp, sinkdp, data)
                self._put_data(sourcedp, sinkdp, data, dataRid)

            cnt = cnt+1
            self.cond.emit("sync-progress", float(cnt)/total)

        #FIXME: rename dp1 -> sourcedp1 and dp2 -> sinkdp2 because when both
        #data is modified we might as well choost source -> sink as the comparison direction
        for dp1, data1UID, dp2, data2UID in tocomp:
            data1 = self._get_data(dp1, dp2, data1UID)
            data1Rid = data1.get_rid()
            data2 = self._get_data(dp2, dp1, data2UID)
            data2Rid = data2.get_rid()
            
            #Only need to convert one data to the other type
            #choose to convert the source data for no reason other than convention
            data1 = self._convert_data(dp1, dp2, data1)
            
            log.debug("2WAY CMP: %s v %s" % (data1, data2))

            cnt = cnt+1
            self.cond.emit("sync-progress", float(cnt)/total)

            #compare the data
            if data1 != None and data2 != None:
                comparison = data1.compare(data2)
                if comparison == conduit.datatypes.COMPARISON_OLDER:
                    self._apply_conflict_policy(dp2, dp1, COMPARISON_UNKNOWN, data2, data2Rid, data1, data1Rid)
                else:
                    self._apply_conflict_policy(dp1, dp2, COMPARISON_UNKNOWN, data1, data1Rid, data2, data2Rid)

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
            log.debug("Sync %s beginning. Slow: %s, Twoway: %s" % (
                                    self,
                                    self.cond.do_slow_sync(), 
                                    self.cond.is_two_way()
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
            self.cond.emit("sync-started")
            while not finished:
                self.check_thread_not_cancelled([self.source] + self.sinks)
                log.debug("Syncworker state %s" % self.state)

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
                        log.warn("Not enough configured datasinks")
                        self.aborted = True
                        self.state = SyncWorker.DONE_STATE                  

                #refresh state
                elif self.state is SyncWorker.REFRESH_STATE:
                    log.debug("Source Status = %s" % self.source.module.get_status_text())
                    #Refresh the source
                    try:
                        self.source.module.refresh()
                        self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
                    except Exceptions.RefreshError:
                        self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                        log.warn("RefreshError: %s" % self.source)
                        #Cannot continue with no source data
                        raise Exceptions.StopSync
                    except Exception:
                        log.critical("UNKNOWN REFRESH ERROR: %s\n%s" % (self.source,traceback.format_exc()))
                        self.source.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
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
                                log.warn("RefreshError: %s" % sink)
                                sinkDidntRefreshOK[sink] = True
                                self.sinkErrors[sink] = DataProvider.STATUS_DONE_REFRESH_ERROR
                            except Exception:
                                log.critical("UNKNOWN REFRESH ERROR: %s\n%s" % (sink,traceback.format_exc()))
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
                        log.info("Not enough sinks refreshed")
                        self.aborted = True
                        self.state = SyncWorker.DONE_STATE                        

                #synchronize state
                elif self.state is SyncWorker.SYNC_STATE:
                    for sink in self.sinks:
                        self.check_thread_not_cancelled([self.source, sink])
                        #only sync with those sinks that refresh'd OK
                        if sink not in sinkDidntRefreshOK:
                            #now perform a one or two way sync depending on the user prefs
                            #and the capabilities of the dataprovider
                            if  self.cond.is_two_way():
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
                    
                    #Exit thread
                    finished = True

        except Exceptions.StopSync:
            log.warn("Sync Aborted")
            self.aborted = True

        #Post sync cleanup and notification of sync success
        error = self.did_sync_error()
        conflict = self.did_sync_conflict()
        for s in [self.source] + self.sinks:
            s.module.finish(self.aborted, error, conflict)
        conduit.GLOBALS.mappingDB.save()
        self.cond.emit("sync-completed", self.aborted, error, conflict)

class RefreshDataProviderWorker(_ThreadedWorker):
    """
    Refreshes a single dataprovider, handling any errors, etc
    """

    def __init__(self, cond, dataproviderWrapper):
        """
        @param dataproviderWrapper: The dp to refresh
        """
        _ThreadedWorker.__init__(self)
        self.dataproviderWrapper = dataproviderWrapper
        self.cond = cond

        self.setName("%s" % self.dataproviderWrapper)

    def run(self):
        """
        The main refresh state machine.
        
        Takes the conduit through the init->is_configured->refresh
        steps, setting its status at the appropriate time and performing
        nicely in the case of errors. 
        """
        try:
            log.debug("Refresh %s beginning" % self)
            self.cond.emit("sync-started")

            if not self.dataproviderWrapper.module.is_configured():
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_SYNC_NOT_CONFIGURED)
                #Cannot continue if source not configured
                raise Exceptions.StopSync
        
            try:
                self.dataproviderWrapper.module.refresh()
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_REFRESH_OK)
            except Exceptions.RefreshError:
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                log.warn("RefreshError: %s" % self.dataproviderWrapper)
                #Cannot continue with no source data
                raise Exceptions.StopSync
            except Exception:
                self.dataproviderWrapper.module.set_status(DataProvider.STATUS_DONE_REFRESH_ERROR)
                log.critical("UNKNOWN REFRESH ERROR: %s\n%s" % (self.dataproviderWrapper,traceback.format_exc()))
                #Cannot continue with no source data
                raise Exceptions.StopSync           

        except Exceptions.StopSync:
            log.warn("Sync Aborted")
            self.aborted = True

        conduit.GLOBALS.mappingDB.save()
        self.cond.emit("sync-completed", self.aborted, self.did_sync_error(), self.did_sync_conflict())

                
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
        
    def get_rid(self):
        return Rid(self.UID)
        
    def get_snippet(self):
        return self.snippet

    def get_open_URI(self):
        return None

    def __str__(self):
        return "Deleted Data: %s" % self.UID
