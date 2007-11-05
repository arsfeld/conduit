"""
Contains classes for transmitting and receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""

import socket
import xmlrpclib
import SimpleXMLRPCServer
import pickle
import threading

import conduit
from conduit import log,logd,logw
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import Peers

SERVER_PORT = 3400
DP_PORT = 3401

class NetworkServerFactory(DataProvider.DataProviderFactory):
    """
    Controlls all network related communication aspects. This involves
    1) Advertising dataprovider presence on local network using avahi
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self)

        self.conduits = {}
        self.shared = {}

        #watch the modulemanager for added conduits and syncsets
        conduit.GLOBALS.moduleManager.connect('syncset-added', self._syncset_added)

        # Initiate Avahi stuff & announce our presence
        self.advertiser = Peers.AvahiAdvertiser("_conduit.tcp", SERVER_PORT)
        self.advertiser.announce()

        # start the server which anounces other shared servers
        self.rootServer = StoppableXMLRPCServer('',SERVER_PORT)
        self.rootServer.register_function(self.list_shared_dataproviders)
        self.rootServer.start()

    def list_shared_dataproviders(self):
        info = {}
        for key, dp in self.shared.iteritems():
            info[key] = dp.get_info()
        return info

    def quit(self):
        self.rootServer.stop()

    def _syncset_added(self, mgr, syncset):
        syncset.connect("conduit-added", self._conduit_added)
        syncset.connect("conduit-removed", self._conduit_removed)

    def _conduit_added(self, syncset, conduit):
        conduit.connect("dataprovider-added", self._conduit_changed)
        conduit.connect("dataprovider-removed", self._conduit_changed)

    def _conduit_removed(self, syncset, conduit):
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

    def _conduit_changed(self, conduit, dataprovider):
        """
        Same event handler for dataprovider-added + removed
        """
        shared = self._get_shared(conduit)
        if shared != None:
            if conduit not in self.conduits:
                self.share_dataprovider(conduit, shared)
        else:
            if conduit in self.conduits:
                self.unshare_dataprovider(conduit)

    def share_dataprovider(self, conduit, dataprovider):
        """
        Shares a conduit/dp on the network
        """
        server = DataproviderResource(dataprovider, DP_PORT)
        server.start()
        self.shared[conduit.uid] = server

    def unshare_dataprovider(self, conduit):
        """
        Stop sharing a conduit
        """
        if conduit.uid in self.conduits:
            server = self.shared[conduit.uid]
            server.stop()
            del self.shared[conduit.uid]

class NetworkEndpoint(DataProvider.TwoWay):

    _name_ = "Network"
    _description_ = "Network your desktop"
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "gnome-nettool"

    def is_busy(self):
        return True

    def get_UID(self):
        return "NetworkEndpoint"

class StoppableXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """
    Wrapper around a SimpleXMLRpcServer that allows threaded 
    operation and cancellation
    """
    allow_reuse_address = True
    def __init__( self, host, port):
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,(host,port))

    def server_bind(self):
        SimpleXMLRPCServer.SimpleXMLRPCServer.server_bind(self)
        self.socket.settimeout(1)
        self.stop_request = False
        
    def get_request(self):
        while not self.stop_request:
            try:
                sock, addr = self.socket.accept()
                sock.settimeout(None)
                return (sock, addr)
            except socket.timeout:
                pass
            return (None,None)
        
    def close_request(self, request):
        if (request is None): return
        SimpleXMLRPCServer.SimpleXMLRPCServer.close_request(self, request)
        
    def process_request(self, request, client_address):
        if (request is None): return
        SimpleXMLRPCServer.SimpleXMLRPCServer.process_request(self, request, client_address)
        
    def start(self):
        threading.Thread(target=self.serve).start()
        
    def stop(self):
        self.stop_request = True

    def serve(self):
        while not self.stop_request:
            self.handle_request()

class DataproviderResource(StoppableXMLRPCServer):
    def __init__(self, wrapper, port):
        StoppableXMLRPCServer.__init__(self,'',port)
        self.port = port
        self.dpw = wrapper

        #register individual functions, not the whole object, 
        #because we need to pickle function arguments
        self.register_function(self.get_info)

    def get_info(self):
        """
        Return information about this dataprovider (so that client can show correct icon, name, description etc)
        """
        return {"uid":          self.dpw.module.get_UID(),
                "name":         self.dpw.name,
                "description":  self.dpw.description,
                "icon":         self.dpw.icon_name,
                "module_type":  self.dpw.module_type,
                "in_type":      self.dpw.in_type,
                "out_type":     self.dpw.out_type,
                "server_port":  self.port                 
                }

    def get_all(self):
        self.dpw.module.refresh()
        return self.dpw.module.get_all()

    def get(self, LUID):
        return xmlrpclib.Binary(pickle.dumps(self.dpw.module.get(LUID)))

    def put(self, data, overwrite, LUID):
        data = pickle.loads(str(data))
        if len(LUID) == 0:
            LUID = None
        try:
            return self.dpw.module.put(data, overwrite, LUID)
        except Exceptions.SynchronizeConflictError, e:
            return xmlrpclib.Fault("SynchronizeConflictError", e.comparison)

    def delete(self, LUID):
        self.dpw.module.delete(LUID)
        return ""
