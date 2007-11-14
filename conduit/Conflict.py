"""
Holds classes used for resolving conflicts.

Copyright: John Stowers, 2006
License: GPLv2
"""
#ENUM of directions when resolving a conflict
CONFLICT_SKIP = 0                   #dont draw an arrow - draw a -x-
CONFLICT_COPY_SOURCE_TO_SINK = 1    #right drawn arrow
CONFLICT_COPY_SINK_TO_SOURCE = 2    #left drawn arrow
CONFLICT_DELETE = 3                 #double headed arrow

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


