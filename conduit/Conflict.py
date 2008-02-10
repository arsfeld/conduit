"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""
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
    def __init__(self, sourceWrapper, sourceData, sourceDataRid, sinkWrapper, sinkData, sinkDataRid, validResolveChoices, isDeletion):
        self.sourceWrapper = sourceWrapper
        self.sourceData = sourceData
        self.sourceDataRid = sourceDataRid
        self.sinkWrapper = sinkWrapper
        self.sinkData = sinkData
        self.sinkDataRid = sinkDataRid
        self.choices = validResolveChoices
        self.isDeletion = isDeletion


