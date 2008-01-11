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
import select
import logging
log = logging.getLogger("modules.Network")

import Peers
import XMLRPCUtils

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions

from gettext import gettext as _

SERVER_PORT = 3400

class NetworkServerFactory(DataProvider.DataProviderFactory):
    """
    Controlls all network related communication aspects. This involves
    1) Advertising dataprovider presence on local network using avahi
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self)

        self.shared = {}
        self.DP_PORT = 3401

        #watch the modulemanager for added conduits and syncsets
        if conduit.GLOBALS.moduleManager != None:
            conduit.GLOBALS.moduleManager.connect('syncset-added', self._syncset_added)
            # Initiate Avahi stuff & announce our presence
            try:
                self.advertiser = Peers.AvahiAdvertiser("_conduit.tcp", SERVER_PORT)
                self.advertiser.announce()
    
                # start the server which anounces other shared servers
                self.peerAnnouncer = _StoppableXMLRPCServer('',SERVER_PORT)
                self.peerAnnouncer.register_function(self.list_shared_dataproviders)
                self.peerAnnouncer.start()
            except:
                log.warn("Error starting server")
            
        else:
            log.warn("Could not start server, moduleManager not created yet")



    def list_shared_dataproviders(self):
        info = []
        for key, dp in self.shared.iteritems():
            info.append(dp.get_info())
        return info

    def quit(self):
        #stop all the xmlrpc servers
        self.peerAnnouncer.stop()
        for server in self.shared.values():
            server.stop()

    def _syncset_added(self, mgr, syncset):
        syncset.connect("conduit-added", self._conduit_added)
        syncset.connect("conduit-removed", self._conduit_removed)

    def _conduit_added(self, syncset, conduit):
        conduit.connect("dataprovider-added", self._dataprovider_added)
        conduit.connect("dataprovider-removed", self._dataprovider_removed)

    def _conduit_removed(self, syncset, conduit):
        pass

    def _get_shared_dps(self, conduit):
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

    def _dataprovider_added(self, cond, dpw):
        sharedDpw = self._get_shared_dps(cond)
        if sharedDpw != None:
            if sharedDpw.get_UID() not in self.shared:
                self.share_dataprovider(sharedDpw)

    def _dataprovider_removed(self, cond, dpw):
        if dpw.get_UID() in self.shared:
            self.unshare_dataprovider(dpw)

    def share_dataprovider(self, dpw):
        """
        Shares a conduit/dp on the network
        """
        server = _DataproviderServer(dpw, self.DP_PORT)
        server.start()
        self.shared[dpw.get_UID()] = server
        self.DP_PORT += 1

    def unshare_dataprovider(self, dpw):
        """
        Stop sharing a conduit
        """
        uid = dpw.get_UID()
        server = self.shared[uid]
        server.stop()
        del self.shared[uid]

class NetworkEndpoint(DataProvider.TwoWay):
    """
    Simple class used for detecting when a user connects
    another dataprovider to this one, symbolising a network sync
    """
    _name_ = _("Network")
    _description_ = _("Network your desktop")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "gnome-nettool"

    def is_busy(self):
        return True

    def get_UID(self):
        return "NetworkEndpoint"

class _StoppableXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """
    A variant of SimpleXMLRPCServer that can be stopped. From
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/520583
    """
    allow_reuse_address = True
    def __init__( self, host, port):
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,
                                addr=(host,port),
                                logRequests=False,
                                allow_none=True
                                )
        self.closed = False
    
    def serve(self):
        self.socket.setblocking(0)
        while not self.closed:
            self.handle_request()        
            
    def get_request(self):
        inputObjects = []
        while not inputObjects and not self.closed:
            try:
                inputObjects, outputObjects, errorObjects = select.select([self.socket], [], [], 0.2)
                return self.socket.accept()
            except select.error:
                #Occurs sometimes at start up, race condition, ignore
                pass
            except socket.error:
                #Occurs at shutdown, raise to stop serving
                raise
                
    def start(self):
        threading.Thread(target=self.serve).start()
        
    def stop(self):
        self.closed = True

class _DataproviderServer(_StoppableXMLRPCServer):
    """
    Wraps a dataproviderwrapper in order to pickle args
    and deal with exceptions in the sync process
    """
    def __init__(self, wrapper, port):
        _StoppableXMLRPCServer.__init__(self,'',port)
        self.port = port
        self.dpw = wrapper
        
        #Additional functions not part of the normal dp api
        self.register_function(self.get_info)

        #register individual functions, not the whole object, 
        #because in some cases we need to pickle function arguments
        #and deal with exceptions
        self.register_function(self.refresh)
        self.register_function(self.get_all)
        self.register_function(self.get)
        self.register_function(self.put)
        self.register_function(self.delete)
        self.register_function(self.finish)

    def get_info(self):
        """
        Return information about this dataprovider 
        (so that client can show correct icon, name, description etc)
        """
        return {"uid":              self.dpw.get_UID(),
                "name":             self.dpw.name,
                "description":      self.dpw.description,
                "icon":             self.dpw.icon_name,
                "module_type":      self.dpw.module_type,
                "in_type":          self.dpw.in_type,
                "out_type":         self.dpw.out_type,
                "dp_server_port":   self.port                 
                }

    def refresh(self):
        try:
            self.dpw.module.refresh()
        except Exception, e:
            return XMLRPCUtils.marshal_exception_to_fault(e)

    def get_all(self):
        try:
            return self.dpw.module.get_all()
        except Exception, e:
            return XMLRPCUtils.marshal_exception_to_fault(e)

    def get(self, LUID):
        try:
            return xmlrpclib.Binary(pickle.dumps(self.dpw.module.get(LUID)))
        except Exception, e:
            return XMLRPCUtils.marshal_exception_to_fault(e)

    def put(self, binaryData, overwrite, LUID):
        data = pickle.loads(binaryData.data)
        try:
            rid = self.dpw.module.put(data, overwrite, LUID)
            return xmlrpclib.Binary(pickle.dumps(rid))
        except Exception, e:
            return XMLRPCUtils.marshal_exception_to_fault(e)

    def delete(self, LUID):
        try:
            self.dpw.module.delete(LUID)
        except Exception, e:
            return XMLRPCUtils.marshal_exception_to_fault(e)

    def finish(self, aborted, error, conflict):
        try:
            self.dpw.module.finish()
        except Exception, e:
            return XMLRPCUtils.marshal_exception_to_fault(e)
            

