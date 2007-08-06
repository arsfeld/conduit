"""
Contains classes for transmitting and receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import Peers

from twisted.internet import reactor
from twisted.web import resource, server, xmlrpc
import xmlrpclib, pickle, threading

SERVER_PORT = 3400

class NetworkServerFactory(DataProvider.DataProviderFactory, gobject.GObject, threading.Thread):
    """
    Controlls all network related communication aspects. This involves
    1) Advertising dataprovider presence on local network using avahi
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)
        threading.Thread.__init__(self)

        if not kwargs.has_key("moduleManager"):
            return

        self.modules = kwargs['moduleManager']
        self.modules.connect('syncset-added', self.syncset_added)
        self.start()

    def run(self):
        self.conduits = {}
        self.shared = {}

        # Initiate Avahi stuff & announce our presence
        self.advertiser = Peers.AvahiAdvertiser("_conduit.tcp", SERVER_PORT)
        self.advertiser.announce()
        
        # Create a XML-RPC server..
        reactor.listenTCP(SERVER_PORT, server.Site(RootResource(self)))
        reactor.run(installSignalHandlers=0)

    def quit(self):
        reactor.stop()

    def syncset_added(self, mgr, syncset):
        syncset.connect("conduit-added", self.conduit_added)
        syncset.connect("conduit-removed", self.conduit_removed)

    def conduit_added(self, syncset, conduit):
        conduit.connect("dataprovider-added", self.conduit_changed)
        conduit.connect("dataprovider-removed", self.conduit_changed)

    def conduit_removed(self, syncset, conduit):
        pass

    def _get_shared(self, conduit):
        """
        This is a cludgy evil function to determine if a conduit is shared or not
          If it is, the dp to share is returned
          If it is not, None is returned
        """
        dps = conduit.get_all_dataproviders()
        ne = None
        tg = None
        if len(dps) == 2:
            for dp in dps:
                if type(dp.module) == NetworkEndpoint:
                    ne = dp
                else:
                    tg = dp
            if tg and ne:
                return tg
            else:
                return None
        return None

    def conduit_changed(self, conduit, dataprovider):
        """
        Same event handler for dataprovider-added + removed
        """
        shared = self._get_shared(conduit)
        if shared != None:
            if not conduit in self.conduits:
                instance = self.modules.get_new_module_instance(shared.get_key())
                self.share_dataprovider(conduit, instance)
        else:
            if conduit in self.conduits:
                self.unshare_dataprovider(conduit)

    def share_dataprovider(self, conduit, dataprovider):
        """
        Shares a conduit/dp on the network
        """
        self.shared[conduit.uid] = DataproviderResource(dataprovider, conduit.uid)
        self.advertiser.announce()

    def unshare_dataprovider(self, conduit):
        """
        Stop sharing a conduit
        """
        if conduit in self.conduits:
            del self.shared[conduit.uid]
        self.advertiser.announce()

class NetworkEndpoint(DataProvider.TwoWay):

    _name_ = "Network"
    _description_ = "Network your desktop"
    _category_ = DataProvider.CATEGORY_NOTES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "tomboy"

    def is_busy(self):
        return True

    def get_UID(self):
        return "NetworkEndpoint"

class RootResource(xmlrpc.XMLRPC):
    isLeaf = False

    def __init__(self, factory):
        xmlrpc.XMLRPC.__init__(self)
        self.factory = factory

    def xmlrpc_get_all(self):
        info = {}
        for key, dp in self.factory.shared.iteritems():
            info[key] = dp.get_info()
        return info

    def getChild(self, path, request):
        if path == "":
            return self
        elif self.factory.shared.has_key(path):
            return self.factory.shared[path]

class DataproviderResource(xmlrpc.XMLRPC):
    def __init__(self, wrapper, uid):
        xmlrpc.XMLRPC.__init__(self)
        self.uid = uid
        self.wrapper = wrapper
        self.module = wrapper.module

    def get_info(self):
        """
        Return information about this dataprovider (so that client can show correct icon, name, description etc)
        """
        wrapper = self.wrapper
        return { "uid":          self.uid,
                 "name":         wrapper.name,
                 "description":  wrapper.description,
                 "icon":         wrapper.icon_name,
                 "module_type":  wrapper.module_type,
                 "in_type":      wrapper.in_type,
                 "out_type":     wrapper.out_type,
               }

    def xmlrpc_get_info(self):
        return self.get_info()

    def xmlrpc_get_all(self):
        self.module.refresh()
        return self.module.get_all()

    def xmlrpc_get(self, LUID):
        return xmlrpclib.Binary(pickle.dumps(self.module.get(LUID)))

    def xmlrpc_put(self, data, overwrite, LUID):
        data = pickle.loads(str(data))
        if len(LUID) == 0:
            LUID = None
        try:
            return self.module.put(data, overwrite, LUID)
        except Exceptions.SynchronizeConflictError, e:
            return xmlrpclib.Fault("SynchronizeConflictError", e.comparison)

    def xmlrpc_delete(self, LUID):
        self.module.delete(LUID)
        return ""
