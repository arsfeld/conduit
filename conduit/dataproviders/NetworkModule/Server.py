"""
Contains classes for transmitting and receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject

import conduit
from conduit import log,logd,logw
from conduit.ModuleWrapper import ModuleWrapper
import conduit.Module as Module
import conduit.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import Peers

from twisted.internet import reactor
from twisted.web import resource, server, xmlrpc
import xmlrpclib, pickle, threading

SERVER_PORT = 3400

class NetworkServerFactory(Module.DataProviderFactory, gobject.GObject, threading.Thread):
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
        self.start()

    def run(self):
        self.shared = {}

        self.advertiser = Peers.AvahiAdvertiser("_conduit.tcp", SERVER_PORT)
        self.advertiser.announce()
        
        reactor.listenTCP(SERVER_PORT, server.Site(RootResource(self)))
        
        # After a short delay share some services
        gobject.timeout_add(1000, self.test_cb)

        reactor.run(installSignalHandlers=0)

    def quit(self):
        reactor.stop()

    def test_cb(self):
        for wrapper in self.modules.get_modules_by_type(None):
            if wrapper.get_key() in ("TomboyNoteTwoWay", "EvoContactTwoWay"):
                instance = self.modules.get_new_module_instance(wrapper.get_key())
                self.share_dataprovider(instance)

    def share_dataprovider(self, dataproviderWrapper):
        """
        Shares a dataprovider on the network
        """
        self.shared[dataproviderWrapper.get_UID().encode("hex")] = DataproviderResource(dataproviderWrapper)
        self.advertiser.announce()

    def unshare_dataprovider(self, dataproviderWrapper):
        """
        Stop sharing a dataprovider
        """
        if self.shared.has_key(dataproviderWrapper.get_key()):
            self.shared.remove(dataproviderWrapper.get_key())
        self.advertiser.announce()

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
    def __init__(self, wrapper):
        xmlrpc.XMLRPC.__init__(self)
        self.wrapper = wrapper
        self.module = wrapper.module

    def get_info(self):
        """
        Return information about this dataprovider (so that client can show correct icon, name, description etc)
        """
        wrapper = self.wrapper
        return { "uid":          wrapper.get_UID().encode("hex"),
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
