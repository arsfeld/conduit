"""
Represents a conduit (The joining of one source to one or more sinks)

Copyright: John Stowers, 2006
License: GPLv2
"""
from conduit import log,logd,logw
import gobject

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
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    # The DataProvider that was added to this ConduitModel
        "dataprovider-removed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    # The DataProvider that was added to this ConduitModel
        }

    def __init__(self):
        """
        Makes and empty conduit ready to hold one datasource and many
        datasinks
        """
        gobject.GObject.__init__(self)

        #a conduit can hold one datasource and many datasinks (wrappers)
        self.datasource = None
        self.datasinks = []

        self.twoWaySyncEnabled = False
        self.slowSyncEnabled = False
                                                
    def add_dataprovider(self, dataprovider_wrapper, isSource=False):
        """
        Adds a dataprovider to the conduit.
        
        @param dataprovider_wrapper: The L{conduit.Module.ModuleWrapper} 
        containing a L{conduit.DataProvider.DataProviderBase} to add
        @type dataprovider_wrapper: L{conduit.Module.ModuleWrapper}
        """
        if dataprovider_wrapper.module_type == "source" or isSource:
            #only one source is allowed
            if self.datasource == None:
                self.datasource = dataprovider_wrapper
            else:         
                logw("Only one datasource allowed per conduit")
                return

        elif dataprovider_wrapper.module_type == "sink":
            #only one sink of each kind is allowed
            if dataprovider_wrapper in self.datasinks:
                logw("This datasink already present in this conduit")
                return
            else:
                #temp reference for drawing the connector line
                self.datasinks.append(dataprovider_wrapper)

        elif dataprovider_wrapper.module_type == "twoway":
            if self.datasource == None:
                logd("Adding twoway dataprovider into source position")
                self.datasource = dataprovider_wrapper
            else:
                logd("Adding twoway dataprovider into sink position")
                self.datasinks.append(dataprovider_wrapper)
                #Datasinks go on the right
        else:
                logw("Only sinks, sources or twoway dataproviders may be added")
                return


        #Check if a two way sync can still be performed
        if not self.can_do_two_way_sync():
            self.disable_two_way_sync()

        gobject.idle_add(self.emit, "dataprovider-added", dataprovider_wrapper) 

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
        Tests if it is currently safe to modify the conduits settings
        or start/restart as synchronisation. 
        
        @returns: True if the conduit is currenlty performing a synchronisation
        operaton on one or more of its contained DataProviders
        @rtype: C{bool}
        """
        for sink in self.datasinks + [self.datasource]:
            if sink is not None:
                if sink.module.is_busy():
                    return True
                
        return False
        
    def has_dataprovider(self, dataprovider):
        """
        Checks if the conduit containes the specified dataprovider
        
        @type dataprovider: L{Conduit.Module.ModuleWrapper}
        @returns: True if the conduit contains the dataprovider
        @rtype: C{bool}
        """
        if dataprovider in self.datasinks + [self.datasource]:
            return True
        else:
            return False

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
        gobject.idle_add(self.emit, "dataprovider-removed", dataprovider)

        #Sources and sinks are stored seperately so must be deleted from different
        #places. Lucky there is only one source or this would be harder....
        if dataprovider == self.datasource:
            del(self.datasource)
            self.datasource = None
        elif dataprovider in self.datasinks:
            i = self.datasinks.index(dataprovider)
            del(self.datasinks[i])
        else:
            logw("Could not remove %s" % dataprovider)

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
        logd("Enabling Two Way Sync")
        self.twoWaySyncEnabled = True
        if self.can_do_two_way_sync():
            self.connectors[self.datasinks[0]].set_two_way(True)
                    
    def disable_two_way_sync(self):
        logd("Disabling Two Way Sync")
        self.twoWaySyncEnabled = False
        if self.can_do_two_way_sync():
            self.connectors[self.datasinks[0]].set_two_way(False)

    def is_two_way(self):
        return self.can_do_two_way_sync() and self.twoWaySyncEnabled

    def enable_slow_sync(self):
        self.slowSyncEnabled = True

    def disable_slow_sync(self):
        self.slowSyncEnabled = False

    def do_slow_sync(self):
        return self.slowSyncEnabled


