"""
Shared API for comparing the previous state of a dp to the current 
state. Returns only changes to core synch mechanism.

This class is a proxy for the TwoWay dataprovider. If the dataprovider
cannot implement get_changes() using backend dependant means this class 
uses the mapping DB to implement get_changes()

This class will always be slower than if the backend implements the function
iteself.

Copyright: John Stowers, 2006
License: GPLv2
"""
import logging
log = logging.getLogger("DeltaProvider")

import conduit

class DeltaProvider:
    def __init__(self, dpw, otherdpw):
        self.me = dpw
        self.other = otherdpw

        log.info("Delta: Source (%s) does not implement get_changes(). Proxying..." % self.me.get_UID())

    def get_changes(self):
        """
        @returns: added, modified, deleted
        """
        allItems = []
        for i in self.me.module.get_all():
            #Make sure the are in unicode to assure a 
            #good comparison with mapping UID's
            if type(i) != unicode:
                i = unicode(i,errors='replace')
            allItems.append(i)

        log.debug("Delta: Got %s items\n%s" % (len(allItems), allItems))

        #In order to detect deletions we need to fetch all the existing relationships.
        #we also get the rids because we need those to detect if something has changed
        rids = {}
        for m in conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(self.me.get_UID(), self.other.get_UID()):
            rids[ m.get_source_rid().get_UID() ] = m.get_source_rid()
        for m in conduit.GLOBALS.mappingDB.get_mappings_for_dataproviders(self.other.get_UID(), self.me.get_UID()):
            rids[ m.get_sink_rid().get_UID() ] = m.get_sink_rid()

        log.debug("Delta: Expecting %s items" % len(rids))
        for uid,rid in rids.items():
            log.debug("%s) -- %s" % (uid,rid))

        #now classify all my items relative to the expected data from the previous
        #sync with the supplied other dataprovider. Copy (slice) the list because we
        #modify it in place
        modified = []
        for i in allItems[:]:
            if i in rids:
                data = self.me.module.get(i)
                if data.get_rid().get_hash() != rids[i].get_hash():
                    log.debug("Modified: Actual:%s v DB:%s" % (data.get_rid(), rids[i]))
                    modified.append(i)
                del(rids[i])
                allItems.remove(i)

        #now all that remains in rids is data which has been deleted,
        #and all that remains in allItems is new data
        return allItems, modified, rids.keys()

