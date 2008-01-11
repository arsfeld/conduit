"""
Contains classes for transmitting and receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""
import logging
log = logging.getLogger("modules.Network")

import Peers
import XMLRPCUtils

import conduit
import conduit.dataproviders.DataProvider as DataProvider

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
                self.peerAnnouncer = XMLRPCUtils.StoppableXMLRPCServer('',SERVER_PORT)
                self.peerAnnouncer.register_function(self.list_shared_dataproviders)
                self.peerAnnouncer.start()
            except:
                log.warn("Error starting server")
            
        else:
            log.warn("Could not start server, moduleManager not created yet")

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
                return tg,ne
            else:
                return None,None
        return None,None

    def _dataprovider_added(self, cond, dpw):
        sharedDpw,networkEndpoint = self._get_shared_dps(cond)
        if sharedDpw != None:
            if sharedDpw.get_UID() not in self.shared:
                #Update the network enpoint to have the same input and output
                #types as the shared DP. The proper solution here is to
                #have the network endpoint also be a client to the remote dp,
                #but thats not going to happen yet
                networkEndpoint.module.input_type = sharedDpw.module.get_input_type()
                networkEndpoint.module.output_type = sharedDpw.module.get_output_type()
                cond._parameters_changed()
                self.share_dataprovider(sharedDpw)

    def _dataprovider_removed(self, cond, dpw):
        if dpw.get_UID() in self.shared:
            self.unshare_dataprovider(dpw)
            
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

    def share_dataprovider(self, dpw):
        """
        Shares a conduit/dp on the network
        """
        server = XMLRPCUtils.DataproviderServer(dpw, self.DP_PORT)
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
    _icon_ = "gnome-nettool"

    def __init__(self):
        DataProvider.TwoWay.__init__(self)
        self.input_type = ""
        self.output_type = ""

    def is_busy(self):
        return True
        
    def get_input_type(self):
        return self.input_type
        
    def get_output_type(self):
        return self.output_type

    def get_UID(self):
        return "NetworkEndpoint"            

