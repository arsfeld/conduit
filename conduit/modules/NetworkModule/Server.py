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
        
        # Initiate Avahi stuff & announce our presence
        try:
            log.debug("Starting AvahiAdvertiser server")
            self.advertiser = Peers.AvahiAdvertiser("_conduit.tcp", SERVER_PORT)
            self.advertiser.announce()

            #Start the server which anounces other shared servers
            self.peerAnnouncer = XMLRPCUtils.StoppableXMLRPCServer('',SERVER_PORT)
            self.peerAnnouncer.register_function(self.list_shared_dataproviders)
            self.peerAnnouncer.start()
            
            #FIXME: Only show the endpoint if the server was started.
            #self.emit_added(
            #        klass=NetworkEndpoint,
            #        initargs=(), 
            #        category=conduit.dataproviders.CATEGORY_MISC
            #        )
        except Exception, e:
            self.peerAnnouncer = None
            log.warn("Error starting AvahiAdvertiser server: %s" % e)

        #watch the modulemanager for added conduits and syncsets
        if conduit.GLOBALS.moduleManager != None:
            conduit.GLOBALS.moduleManager.connect('syncset-added', self._syncset_added)
        else:
            log.warn("Could not start AvahiAdvertiser server, moduleManager not created yet")

    def _syncset_added(self, mgr, syncset):
        syncset.connect("conduit-added", self._conduit_added)
        syncset.connect("conduit-removed", self._conduit_removed)

    def _conduit_added(self, syncset, cond):
        cond.connect("dataprovider-added", self._dataprovider_added)
        cond.connect("dataprovider-removed", self._dataprovider_removed)

    def _conduit_removed(self, syncset, cond):
        for dpw in cond.get_all_dataproviders():
            self._dataprovider_removed(cond, dpw)

    def _get_shared_dps(self, cond):
        """
        This is a cludgy evil function to determine if a conduit is shared or not
          If it is, the dp to share is returned
          If it is not, None is returned
        """
        dps = cond.get_all_dataproviders()
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
            if sharedDpw.get_UID() not in self.shared and sharedDpw.module != None:
                #Update the network enpoint to have the same input and output
                #types as the shared DP.
                networkEndpoint.module.input_type = sharedDpw.module.get_input_type()
                networkEndpoint.module.output_type = sharedDpw.module.get_output_type()
                cond._parameters_changed()
                self.share_dataprovider(sharedDpw)

    def _dataprovider_removed(self, cond, dpw):
        if dpw.get_UID() in self.shared:
            self.unshare_dataprovider(dpw)
            cond._parameters_changed()
            
    def list_shared_dataproviders(self):
        info = []
        for key, dp in self.shared.iteritems():
            info.append(dp.get_info())
        return info

    def quit(self):
        #stop all the xmlrpc servers
        for server in self.shared.values():
            server.stop()

        if self.peerAnnouncer != None:
            self.peerAnnouncer.stop()

    def share_dataprovider(self, dpw):
        """
        Shares a conduit/dp on the network
        """
        server = XMLRPCUtils.DataproviderServer(dpw, self.DP_PORT)
        server.start()
        self.shared[dpw.get_UID()] = server
        self.DP_PORT += 1
        return server

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
    _description_ = _("Enable synchronization via network")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _icon_ = "network-idle"
    _configurable_ = False

    def __init__(self):
        DataProvider.TwoWay.__init__(self)
        self.input_type = ""
        self.output_type = ""

    def is_busy(self):
        #Stop right click menu
        return True

    def is_configured(self, isSource, isTwoWay):
        #Prevent initiating a sync on the server end by pretending we are
        #not configured
        return False

    def get_status(self):
        #Always show status as ready
        return DataProvider.STATUS_NONE

    def get_input_type(self):
        return self.input_type
        
    def get_output_type(self):
        return self.output_type

    def get_UID(self):
        return "NetworkEndpoint"            

