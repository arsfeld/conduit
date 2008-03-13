"""
Contains classes for transmitting and receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""
import xmlrpclib
import threading
import time
import gobject
import logging
import socket
log = logging.getLogger("modules.Network")

import Peers
import XMLRPCUtils

import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory

class NetworkClientFactory(DataProvider.DataProviderFactory):
    """
    Responsible for making networked Conduit resources available to the user. This includes:
    1) Monitoring Avahi events to detect other Conduit instances on the network
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self)

        self.categories = {}
        self.dataproviders = {}
        self.peers = {}
        try:
            self.monitor = Peers.AvahiMonitor(self.host_available, self.host_removed)
        except:
            log.warn("Error starting client")

    def quit(self):
        for p in self.peers.values():
            p.stop()

    def host_available(self, name, host, address, port, extra_info):
        """
        Callback which is triggered when a dataprovider is advertised on 
        a remote conduit instance
        """
        url = "http://%s" % host
        log.debug("Remote host '%s' detected" % url)

        if not self.peers.has_key(url):
            #Create a category group for this host
            self.categories[url] = DataProviderCategory.DataProviderCategory("On %s" % host, "computer", host)
            # Create a dataproviders list for this host
            self.dataproviders[url] = {}
            # Request all dp's for this host. Because there is no
            # avahi signal when the text entry in a avahi publish group
            # is changed, we must poll detected peers....
            request = _PeerLister(url, port)
            request.connect("complete", self.dataprovider_process)
            request.start()
            self.peers[url] = request

    def host_removed(self, url):
        """
        Callback which is triggered when a host is no longer available
        """
        log.debug("Remote host '%s' removed" % url)
        if self.peers.has_key(url):
            self.categories.remove(url)
            for uid, dp in self.dataproviders[url].items():
                self.dataprovider_removed(dp)
            self.dataproviders.remove(url)
            self.peers.remove(url)

    def dataprovider_process(self, peerLister):
        """
        """
        hostUrl = peerLister.url
        currentSharedDps = self.dataproviders[hostUrl]
        #A remote dps uid is the url + the original dp uid
        remoteSharedDps = {}
        for dpInfo in peerLister.data_out:
            remoteUid = "%s-%s" % (hostUrl,dpInfo['uid'])
            remoteSharedDps[remoteUid] = dpInfo

        #log.debug("Processing Remote Dataprovider: URL:%s\tCurrent dps:%s\tRemote dps:%s" % (hostUrl,currentSharedDps,remoteSharedDps.keys()))
        
        # loop through all dp's 
        for remoteUid,info in remoteSharedDps.items():
            if remoteUid not in currentSharedDps:
                self.dataprovider_added(hostUrl, remoteUid, info)

        for remoteUid in currentSharedDps.keys():
            if remoteUid not in remoteSharedDps:
                self.dataprovider_removed(hostUrl, remoteUid)

    def dataprovider_create(self, hostUrl, uid, info):
        # Each dataprovider is on its own port
        dpUrl = "%s:%s/" % (hostUrl, info['dp_server_port'])
   
        params = {}
        for key, val in info.iteritems():
            params['_' + key + '_'] = val

        params['hostUrl'] = hostUrl
        params['url'] = dpUrl
        params['uid'] = uid
    
        # Actually create a new object type based on XMLRPCUtils.DataProviderClient
        # but with the properties from the remote DataProvider
        newdp = type(dpUrl, (XMLRPCUtils.DataProviderClient, ), params)

        return newdp

    def dataprovider_added(self, hostUrl, uid, info):
        """
        Enroll a dataprovider with Conduit's ModuleManager.
        """
        newdp = self.dataprovider_create(hostUrl, uid, info)

        # Register the new dataprovider with Conduit
        key = self.emit_added(
                          klass=newdp, 
                          initargs=(), #No init args, these are encoded as class params
                          category=self.categories[newdp.hostUrl]
                         )

        # Record the key so we can unregister the dp later (if needed)
        self.dataproviders[hostUrl][newdp.uid] = key

    def dataprovider_removed(self, hostUrl, uid):
        """
        Remove a dataprovider from ModuleManager
        """
        self.emit_removed(self.dataproviders[hostUrl][uid])
        del(self.dataproviders[hostUrl][uid])

class _PeerLister(threading.Thread, gobject.GObject):
    """
    Connects to the remote dataprovider factory and queries
    the shared dataproviders
    """
    __gsignals__ =  { 
                    "complete": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    FREQ = 5
    SLEEP = 0.1

    def __init__(self, url, port):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.port = port
        self.url = url
        self.stopped = False
        self._ticks = 0

    def stop(self):
        self.stopped = True

    def run(self):
        server = xmlrpclib.Server("%s:%s/" % (self.url,self.port))
        #Gross cancellable spinning loop...
        while not self.stopped:
            if self._ticks > (self.FREQ / self.SLEEP):
                try:
                    self.data_out = server.list_shared_dataproviders()
                    gobject.idle_add(self.emit, "complete")
                except:
                    #If the server has died or not started yet
                    pass
                self._ticks = 0
            else:
                time.sleep(self.SLEEP)
                self._ticks += 1

