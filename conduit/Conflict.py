"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""
import logging
log = logging.getLogger("Conflict")

import conduit

#ENUM of directions when resolving a conflict
CONFLICT_ASK = 0                    
CONFLICT_SKIP = 1
CONFLICT_COPY_SOURCE_TO_SINK = 2
CONFLICT_COPY_SINK_TO_SOURCE = 3
CONFLICT_DELETE = 4

class Conflict:
    """
    Represents a conflict
    """
    def __init__(self, cond, sourceWrapper, sourceData, sourceDataRid, sinkWrapper, sinkData, sinkDataRid, validResolveChoices, isDeletion):
        self.cond = cond
        self.sourceWrapper = sourceWrapper
        self.sourceData = sourceData
        self.sourceDataRid = sourceDataRid
        self.sinkWrapper = sinkWrapper
        self.sinkData = sinkData
        self.sinkDataRid = sinkDataRid
        self.choices = validResolveChoices
        self.isDeletion = isDeletion

        self._gen_hash()

    def _gen_hash(self):
        if self.sourceWrapper and self.sourceDataRid and self.sinkWrapper:
            mapping = conduit.GLOBALS.mappingDB.get_mapping(
                                sourceUID=self.sourceWrapper.get_UID(),
                                dataLUID=self.sourceDataRid.get_UID(),
                                sinkUID=self.sinkWrapper.get_UID())

            if mapping.oid:
                self._hash = hash(mapping.oid)
                return

        #approximate a stable hash for the relationship that is invariant
        #based upon the order of source and sink
        uids = [hash(self.sourceWrapper.get_UID()),
                hash(self.sinkWrapper.get_UID()),
                hash(self.sourceDataRid),
                hash(self.sinkDataRid)]
        uids.sort()
        self._hash = hash(tuple(uids))

    def __hash__(self):
        return self._hash

    def get_partnership(self):
        return self.sourceWrapper,self.sinkWrapper

    def get_snippet(self, is_source):
        if is_source:
            return self.sourceData.get_snippet()
        else:
            return self.sinkData.get_snippet()

    def get_icon(self, is_source):
        return None

    def resolve(self, direction):
        resolve = True
        delete = False

        if direction == CONFLICT_ASK:
            log.debug("Not resolving")
            resolve = False
        elif direction == CONFLICT_SKIP:
            log.debug("Skipping conflict")
            resolve = False
        elif direction == CONFLICT_COPY_SOURCE_TO_SINK:
            log.debug("Resolving source data --> sink")
            data = self.sourceData
            dataRid = self.sourceDataRid
            source = self.sourceWrapper
            sourceDataType = self.sourceData.get_type()
            sink = self.sinkWrapper
            sinkDataType = self.sinkWrapper.get_input_type()
        elif direction == CONFLICT_COPY_SINK_TO_SOURCE:
            log.debug("Resolving source <-- sink data")
            data = self.sinkData
            dataRid = self.sinkDataRid
            source = self.sinkWrapper
            sourceDataType = self.sinkData.get_type()
            sink = self.sourceWrapper
            sinkDataType = self.sourceWrapper.get_input_type()
        elif direction == CONFLICT_DELETE:
            log.debug("Resolving deletion  --->")
            data = self.sinkData
            dataRid = self.sinkDataRid
            source = self.sourceWrapper
            sink = self.sinkWrapper
            delete = True
        else:
            log.warn("Unknown resolution")
            resolve = False

        if resolve:
            if delete:
                log.debug("Resolving self. Deleting %s from %s" % (data, sink))
                conduit.Synchronization.delete_data(source, sink, data.get_UID())
            else:
                log.debug("Resolving self. Putting %s --> %s" % (data, sink))
                newdata = conduit.GLOBALS.typeConverter.convert( sourceDataType, sinkDataType, data )
                conduit.Synchronization.put_data(source, sink, newdata, dataRid, True)

            self.cond.resolved_conflict(self)

        return resolve

