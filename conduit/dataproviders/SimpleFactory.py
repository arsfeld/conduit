import logging
log = logging.getLogger("dataproviders.SimpleFactory")

import conduit
import conduit.dataproviders.DataProvider as DataProvider

class SimpleFactory(DataProvider.DataProviderFactory):
    """ 
    Encapsulate the emit_added/emit_removed tracking logic and allow 
    it to be shared with multiple dataprovider factories 
    """

    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)
        self.items = {}

    def item_added(self, key, **kwargs):
        log.info("Item Added: %s" % key)
        cat = self.get_category(key, **kwargs)
        idxs = []
        for klass in self.get_dataproviders(key, **kwargs):
            args = self.get_args(key, **kwargs)
            idx = self.emit_added(klass, args, cat)
            idxs.append(idx)
        self.items[key] = idxs

    def item_removed(self, key):
        log.info("Item Removed: %s" % key)
        if key in self.items:
            for idx in self.items[key]:
                self.emit_removed(idx)
            del(self.items[key])

    def get_category(self, key, **kwargs):
        """ Return a category to contain these dataproviders """
        raise NotImplementedError
    
    def get_dataproviders(self, key, **kwargs):
        """ Return a list of dataproviders for this class of device """
        raise NotImplementedError

    def get_args(self, key, **kwargs):
        raise NotImplementedError

    def is_interesting(self, udi, properties):
        raise NotImplementedError

