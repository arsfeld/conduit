"""
Contains classes for transmitting and receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject

import conduit
from conduit import log,logd,logw
from conduit.dataproviders import DataProvider
from conduit.dataproviders import DataProviderCategory
import conduit.Exceptions as Exceptions

import Peers

from cStringIO import StringIO
import xmlrpclib
import threading
import pickle

class NetworkClientFactory(DataProvider.DataProviderFactory, gobject.GObject):
    """
    Responsible for making networked Conduit resources available to the user. This includes:
    1) Monitoring Avahi events to detect other Conduit instances on the network
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

        self.monitor = Peers.AvahiMonitor(self.host_available, self.host_removed)
        self.categories = {}
        self.dataproviders = {}

    def host_available(self, name, host, address, port, extra_info):
        """
        Callback which is triggered when a dataprovider is advertised on 
        a remote conduit instance
        """
        logd("Remote host '%s' detected" % host)

        # Path to remote data services
        url = "http://" + host + ":" + port + "/"

        # Create a categories group for this host?
        if not self.categories.has_key(url):
            self.categories[url] = DataProviderCategory.DataProviderCategory("On %s" % host, "computer", host)
        
        # Create a dataproviders list for this host
        self.dataproviders[url] = {}

        # Request all dp's for this host
        request = ClientDataproviderList(url)
        request.connect("complete", self.dataprovider_process)
        request.start()

    def host_removed(self, url):
        """
        Callback which is triggered when a host is no longer available
        """
        logd("Remote host '%s' removed" % url)

        if self.categories.has_key(url):
            self.categories.remove(url)
        
        if self.dataproviders.has_key(url):
            for uid, dp in self.dataproviders[url].iteritems():
                self.dataprovider_removed(dp)
            self.dataproviders.remove(url)
                    
    def dataprovider_process(self, huh, response):
        """
        """
        # get some local refs
        dps = self.dataproviders[response.url]
        data = response.data_out

        # loop through all dp's 
        for uid, info in data.iteritems():
            if uid not in dps:
                self.dataprovider_added(response.url, uid, info)

        for uid in dps.iterkeys():
            if uid not in data.iterkeys():
                self.dataprovider_removed

    def dataprovider_create(self, host_url, uid, info):
        newurl = host_url + uid

        params = {}

        if info == None:
            s = xmlrpclib.Server(newurl)
            info = s.get_info()

        for key, val in info.iteritems():
            params['_' + key + '_'] = val

        params['host_url'] = host_url
        params['url'] = newurl

        # Actually create a new object type based on ClientDataProvider
        # but with the properties from the remote DataProvider
        newdp = type(newurl, (ClientDataProvider, ), params)
        return newdp

    def dataprovider_added(self, host_url, uid, info):
        """
        Enroll a dataprovider with Conduit's ModuleManager.
        """
        newdp = self.dataprovider_create(host_url, uid, info)

        # Register the new dataprovider with Conduit
        key = self.emit_added(
                                  newdp, 
                                  (newdp.url, ), 
                                  self.categories[newdp.host_url]
                             )

        # Record the key so we can unregister the dp later (if needed)
        self.dataproviders[host_url][newdp.url] = key

    def dataprovider_removed(self, wrapper):
        """
        Remove a dataprovider from ModuleManager
        """
        self.emit_removed(self.dataproviders[wrapper.host_url][wrapper.url])
        self.dataproviders[wrapper.host_url].remove(wrapper.url)

class ClientDataProvider(DataProvider.TwoWay):
    """
    Provides the client portion of dataprovider proxying.
    """

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)

        self.server = xmlrpclib.Server(self.url)
        self.objects = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.objects = self.server.get_all()

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.objects

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return pickle.loads(str(self.server.get(LUID)))

    def put(self, data, overwrite=False, LUID=None):
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        data_out = xmlrpclib.Binary(pickle.dumps(data))

        if LUID == None:
            LUID_out = ""
        else:
            LUID_out = LUID

        try:
            return self.server.put(data_out, overwrite, LUID_out)
        except xmlrpclib.Fault, f:
            if f.faultCode == "SynchronizeConflictError":
                fromData = self.get(LUID)
                raise Exceptions.SynchronizeConflictError(f.faultString, fromData, data)
            else:
                raise f

    def delete(self, LUID):
        self.server.delete(LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.objects = None

    def get_UID(self):
        return "Networked" + self.url

class ClientDataproviderList(threading.Thread, gobject.GObject):
    __gsignals__ =  { 
                    "complete": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT])      #request,
                    }

    def __init__(self, url):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.url = url

    def run(self):
        server = xmlrpclib.Server(self.url)
        self.data_out = server.get_all()
        gobject.idle_add(self.emit, "complete", self)
