"""
Represents a conduit (The joining of one source to one or more sinks)

Copyright: John Stowers, 2006
License: GPLv2
"""
import gobject
import logging
log = logging.getLogger("Conduit")

import conduit
import conduit.utils as Utils

CONFLICT_POLICY_NAMES = ("conflict", "deleted")
CONFLICT_POLICY_VALUES = ("ask","skip","replace")
CONFLICT_POLICY_VALUE_ICONS = {
    "conflict_ask"      :   "conduit-conflict-ask",
    "conflict_skip"     :   "conduit-conflict-skip",
    "conflict_replace"  :   "conduit-conflict-right",
    "deleted_ask"       :   "conduit-conflict-ask",
    "deleted_skip"      :   "conduit-conflict-skip",
    "deleted_replace"   :   "conduit-conflict-delete"
}
    
class Conduit(gobject.GObject):
    """
    Model of a Conduit, which is a one-to-many bridge of DataSources to
    DataSinks.
    
    @ivar datasource: The DataSource to synchronize from
    @type datasource: L{conduit.Module.ModuleWrapper}
    @ivar datasinks: List of DataSinks to synchronize to
    @type datasinks: L{conduit.Module.ModuleWrapper}[]
    """
    __gsignals__ = {
        #Fired when a new instantiatable DP becomes available. It is described via 
        #a wrapper because we do not actually instantiate it till later - to save memory
        "dataprovider-added" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    # The DataProvider that was added to this ConduitModel
        "dataprovider-removed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    # The DataProvider that was removed from this ConduitModel
        "dataprovider-changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT,      # The old DP
            gobject.TYPE_PYOBJECT]),    # The new DP
        "parameters-changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "sync-conflict": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    #Conflict object
        "sync-completed": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_BOOLEAN,       #True if there was a fatal error
            gobject.TYPE_BOOLEAN,       #True if there was a non fatal error
            gobject.TYPE_BOOLEAN]),     #True if there was a conflict
        "sync-started": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "sync-progress": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_FLOAT,         #percent complete
            gobject.TYPE_PYOBJECT])     #list of successfully completed UIDs
        }

    def __init__(self, syncManager, uid=""):
        """
        Makes and empty conduit ready to hold one datasource and many
        datasinks
        """
        gobject.GObject.__init__(self)

        self.syncManager = syncManager

        if uid == "":
            self.uid = Utils.uuid_string()
        else:
            self.uid = uid

        #a conduit can hold one datasource and many datasinks (wrappers)
        self.datasource = None
        self.datasinks = []
        self.twoWaySyncEnabled = False
        self.slowSyncEnabled = False
        self.autoSyncEnabled = False
        self.conflictPolicy = ""
        self.deletedPolicy = ""

        #set conduits to have the default conflict/deleted policy
        for policyName in CONFLICT_POLICY_NAMES:
            policyValue = conduit.GLOBALS.settings.get("default_policy_%s" % policyName)
            self.set_policy(policyName,policyValue)

        self._conflicts = {}

    def _parameters_changed(self):
        self.emit("parameters-changed")
        
    def _change_detected(self, arg):
        #Dont trigger a sync if we are already synchronising
        if not self.is_busy() and self.do_auto_sync():
            log.debug("Triggering an auto sync...")
            self.sync()

    def emit(self, *args):
        """
        Override the gobject signal emission so that all signals are emitted 
        from the main loop on an idle handler
        """
        gobject.idle_add(gobject.GObject.emit,self,*args)
                                                
    def add_dataprovider(self, dataprovider_wrapper, trySourceFirst=True):
        """
        Adds a dataprovider to the conduit.
        
        @param dataprovider_wrapper: The L{conduit.Module.ModuleWrapper} 
        containing a L{conduit.DataProvider.DataProviderBase} to add
        @type dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        if dataprovider_wrapper.module_type == "source":
            #only one source is allowed
            if self.datasource == None:
                self.datasource = dataprovider_wrapper
            else:         
                log.warn("Only one datasource allowed per conduit")
                return False

        elif dataprovider_wrapper.module_type == "sink":
            #only one sink of each kind is allowed
            if dataprovider_wrapper in self.datasinks:
                log.warn("This datasink already present in this conduit")
                return False
            else:
                #temp reference for drawing the connector line
                self.datasinks.append(dataprovider_wrapper)

        elif dataprovider_wrapper.module_type == "twoway":
            if self.datasource == None:
                if trySourceFirst:
                    log.debug("Adding twoway dataprovider into source position")
                    self.datasource = dataprovider_wrapper
                else:
                    log.debug("Adding twoway dataprovider into sink position")
                    self.datasinks.append(dataprovider_wrapper)
            else:
                log.debug("Adding twoway dataprovider into sink position")
                self.datasinks.append(dataprovider_wrapper)
                #Datasinks go on the right
        else:
                log.warn("Only sinks, sources or twoway dataproviders may be added")
                return False

        if dataprovider_wrapper.module != None:
            dataprovider_wrapper.module.connect("change-detected", self._change_detected)

        self.emit("dataprovider-added", dataprovider_wrapper) 
        return True

    def get_dataprovider_position(self, dataproviderWrapper):
        """
        Returns the dp position, 
        Source = 0,0
        Sink = 1, index
        """
        if dataproviderWrapper == self.datasource:
            return 0, 0
        elif dataproviderWrapper in self.datasinks:
            return 1, self.datasinks.index(dataproviderWrapper)
        else:
            return -1, -1

    def is_busy(self):
        """
        Returns True if the conduit is currenlty performing a synchronisation
        operaton on one or more of its contained DataProviders
        """
        return self.syncManager.sync_in_progress(self)
        
    def get_dataproviders_by_key(self, key):
        """
        Use list comprehension to return all dp's with a given key

        @returns: A list of dataproviders with a given key
        """
        return [dp for dp in [self.datasource] + self.datasinks if dp != None and dp.get_key()==key]

    def get_all_dataproviders(self):
        """
        @returns: A list of dataproviders with a given key
        """
        return [dp for dp in [self.datasource] + self.datasinks if dp != None]

    def is_empty(self):
        """
        @returns: True if the conduit contains no dataproviders
        """
        return self.datasource == None and len(self.datasinks) == 0

    def delete_dataprovider(self, dataprovider):
        """
        Deletes dataprovider
        """
        self.emit("dataprovider-removed", dataprovider)
        
        #needed to close the db in file dataproviders
        if dataprovider.module != None:
            dataprovider.module.uninitialize()

        #Sources and sinks are stored seperately so must be deleted from different
        #places. Lucky there is only one source or this would be harder....
        if dataprovider == self.datasource:
            del(self.datasource)
            self.datasource = None
            return True
        elif dataprovider in self.datasinks:
            i = self.datasinks.index(dataprovider)
            del(self.datasinks[i])
            return True
        else:
            log.warn("Could not remove %s" % dataprovider)
            return False

    def can_do_two_way_sync(self):
        """
        Checks if the conduit is eleigable for two way sync, which is true
        if it has one source and once sink. Two way doesnt make sense in 
        any other case
        """
        if self.datasource != None and len(self.datasinks) == 1:
            return self.datasource.module_type == "twoway" and self.datasinks[0].module_type == "twoway"
        return False

    def enable_two_way_sync(self):
        log.debug("Enabling Two Way Sync")
        self.twoWaySyncEnabled = True
        self._parameters_changed()
                    
    def disable_two_way_sync(self):
        log.debug("Disabling Two Way Sync")
        self.twoWaySyncEnabled = False
        self._parameters_changed()

    def is_two_way(self):
        return self.can_do_two_way_sync() and self.twoWaySyncEnabled

    def enable_slow_sync(self):
        log.debug("Enabling Slow Sync")
        self.slowSyncEnabled = True
        self._parameters_changed()

    def disable_slow_sync(self):
        log.debug("Disabling Slow Sync")
        self.slowSyncEnabled = False
        self._parameters_changed()

    def do_slow_sync(self):
        return self.slowSyncEnabled

    def enable_auto_sync(self):
        log.debug("Enabling Auto Sync")
        self.autoSyncEnabled = True
        self._parameters_changed()

    def disable_auto_sync(self):
        log.debug("Disabling Auto Sync")
        self.autoSyncEnabled = False
        self._parameters_changed()

    def do_auto_sync(self):
        return self.autoSyncEnabled

    def get_policy(self, policy):
        if policy not in CONFLICT_POLICY_NAMES:
            raise Exception("Unknown policy: %s" % policy)
        if policy == "conflict":
            return self.conflictPolicy
        else:
            return self.deletedPolicy
        
    def set_policy(self, policy, value):
        if policy not in CONFLICT_POLICY_NAMES:
            raise Exception("Unknown policy: %s" % policy)
        if value not in CONFLICT_POLICY_VALUES:
            raise Exception("Unknown policy value: %s" % policy)
        if policy == "conflict":
            self.conflictPolicy = value
        else:
            self.deletedPolicy = value

    def change_dataprovider(self, oldDpw, newDpw):
        """
        called when dpw becomes unavailable.
        """
        x,y = self.get_dataprovider_position(oldDpw)
        self.delete_dataprovider(oldDpw)
        self.add_dataprovider(
                    dataprovider_wrapper=newDpw,
                    trySourceFirst=(x==0)
                    )
        if newDpw.module != None:
            newDpw.module.connect("change-detected", self._change_detected)

        self.emit("dataprovider-changed", oldDpw, newDpw) 

    def refresh_dataprovider(self, dp, block=False):
        if dp in self.get_all_dataproviders():
            self.syncManager.refresh_dataprovider(self, dp)
            if block == True:
                self.syncManager.join_one(self)
        else:
            log.warn("Could not refresh dataprovider: %s" % dp)

    def refresh(self, block=False):
        if self.datasource is not None and len(self.datasinks) > 0:
            self.syncManager.refresh_conduit(self)
            if block == True:
                self.syncManager.join_one(self)
        else:
            log.info("Conduit must have a datasource and a datasink")

    def sync(self, block=False):
        if self.datasource is not None and len(self.datasinks) > 0:
            self.syncManager.sync_conduit(self)
            if block == True:
                self.syncManager.join_one(self)
        else:
            log.info("Conduit must have a datasource and a datasink")

    def emit_conflict(self, conflict):
        hc = hash(conflict)
        if hc not in self._conflicts:
            self._conflicts[hc] = conflict
            self.emit("sync-conflict", conflict)

    def resolved_conflict(self, conflict):
        try:
            hc = hash(conflict)
            del(self._conflicts[hc])
        except KeyError:
            log.warn("Unknown conflict")
