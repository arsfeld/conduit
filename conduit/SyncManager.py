import gobject

import conduit
import conduit.TypeConverter as TypeConverter

class SyncManager(gobject.GObject): 
    """
    Given a dictionary of relationships this class synchronizes
    the relevant sinks and sources
    """
    	
    def __init__ (self):
        gobject.GObject.__init__(self)
        pass
