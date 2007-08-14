"""
Shared API for comparing the previous state of a dp to the current 
state. Returns only changes to core synch mechanism.

This class is a proxy for the TwoWay dataprovider. If the dataprovider
cannot implement get_changes() using backend dependant means this
class uses the mapping DB to implement get_changes()

This class will always be slower than if the backend implements the function
iteself.

Copyright: John Stowers, 2006
License: GPLv2
"""
import conduit
from conduit import logd, logw, log
import conduit.DataProvider as DataProvider
import conduit.datatypes.DataType as DataType

class DeltaProvider:
    def __init__(self, dpw, otherdpw):
        self.me = dpw
        self.other = otherdpw

        log("Delta: Source (%s) does not implement get_changes(). Proxying..." % self.me.get_UID())

    def get_changes(self):
        """
        @returns: added, modified, deleted
        """
        #Copy (slice) list for in case there are other sinks to follow
        allItems = self.me.module.get_all()[:]
        logd("Delta: Got %s items\n%s" % (len(allItems), allItems))

        #In order to detect deletions we need to fetch all the existing relationships.
        #we also get the mtimes because we need those to detect if something has changed
        mtimes = {}
        for i in conduit.mappingDB.get_mappings_for_dataproviders(self.me.get_UID(), self.other.get_UID()):
            mtimes[ i["sourceDataLUID"] ] = i["sourceDataMtime"]
        for i in conduit.mappingDB.get_mappings_for_dataproviders(self.other.get_UID(), self.me.get_UID()):
            mtimes[ i["sinkDataLUID"] ] = i["sinkDataMtime"]

        logd("Delta: Expecting %s items\n%s" % (len(mtimes), mtimes.keys()))

        #now classify all my items relative to the expected data from the previous
        #sync with the supplied other dataprovider. Copy (slice) the list because we
        #modify it in place
        modified = []
        for i in allItems[:]:
            if i in mtimes:
                data = self.me.module.get(i)
                if data.get_mtime() != mtimes[i]:
                    modified.append(i)
                del(mtimes[i])
                allItems.remove(i)

        #now all that remains in mtimes is data which has been deleted,
        #and all that remains in allItems is new data
        return allItems, modified, mtimes.keys()


