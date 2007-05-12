"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject

import conduit
from conduit import log,logd,logw
import conduit.Module as Module
import conduit.DataProvider as DataProvider

import Peers

import httplib
from cStringIO import StringIO
import threading

try:
    import xml.etree.ElementTree as ET
except:
    import elementtree.ElementTree as ET


class NetworkClientFactory(Module.DataProviderFactory, gobject.GObject):
    """
    Responsible for making networked Conduit resources available to the user. This includes:
    1) Monitoring Avahi events to detect other Conduit instances on the network
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

        self.monitor = Peers.AvahiMonitor(self.host_available, self.host_removed)
        self.hosts = {}
        self.dataproviders = {}

        gobject.timeout_add(1000, self.make_one)

    def make_one(self):
        self.host_available("Tomboy", "localhost", "Baz", 3400, "")

    def host_available(self, name, host, address, port, extra_info):
        """
        Callback which is triggered when a dataprovider is advertised on 
        a remote conduit instance
        """
        logd("Remote host '%s' detected" % host)

        if not self.hosts.has_key(host):
            self.hosts[host] = {}
            self.hosts[host]["category"] = DataProvider.DataProviderCategory("On %s" % host, "computer", host)

        request = Request(host, port, "GET", "/")
        request.connect("complete", self.parse_host_xml)
        request.start()

    def host_removed(self, host):
        """
        Callback which is triggered when a host is no longer available
        """
        if self.hosts.has_key(name):
            logd("Remote host '%s' removed" % name)
            
            for uid, dp in self.dataproviders.iteritems():
                if dp._host_ == host:
                    self.dataprovider_removed(dp)
                    

    def dataprovider_added(self, dataprovider):
        """
        Enroll a dataprovider with Conduit's ModuleManager.
        """
        # Register a dataprovider with Conduit
        key = self.emit_added(
                                  dataprovider, 
                                  (dataprovider._host_, ), 
                                  self.hosts[dataprovider._host_]["category"]
                             )

        # Record the key so we can unregister the dp later (if needed)
        self.dataproviders[dataprovider._guid_] = {
                                                       "local_key" : key,
                                                  }

    def dataprovider_removed(self, wrapper):
        """
        Remove a dataprovider from ModuleManager
        """
        self.emit_removed(self.dataproviders[wrapper._guid_]['local_key'])
        del self.dataproviders[wrapper._guid_]

    def parse_host_xml(self, huh, response):
        for event, elem in ET.iterparse(StringIO(response.out_data)):
            if elem.tag == "dataprovider":
                guid = response.host + ":" + elem.findtext("uid")

                params = {
                             "_name_":        elem.findtext("name"),
                             "_description_": elem.findtext("description"),
                             "_icon_":        elem.findtext("icon"),
                             "_module_type_": elem.findtext("module_type"),
                             "_in_type_":     elem.findtext("in_type"),
                             "_out_type_":    elem.findtext("out_type"),
                             "_uid_":         elem.findtext("uid"),
                             "_host_":        response.host,
                             "_port_":        response.port,
                             "_guid_":        guid,
                         }

                new_dp = type(guid, (ClientDataProvider, ), params)
                self.dataprovider_added(new_dp)

                elem.clear()

class ClientDataProvider(DataProvider.TwoWay):
    """
    Provides the client portion of dataprovider proxying.
    """

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.base = "/%s" % self._uid_
        self.objects = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.objects = []

        response = Request(self._host_, self._port_, "PUT", self.base).get()
        for event, elem in ET.iterparse(StringIO(response)):
            if elem.tag == "object":
                uid = elem.findtext("uid")
                mtime = elem.findtext("mtime")
                elem.clear()

                self.objects.append(uid)

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.objects)

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        uid = self.objects[index]
        request = Request(self._host_, self._port_, "GET", self.base + "/" + uid).get()
        return None

    def put(self, data, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        request = Request(self._host_, self._port_, "PUT", self.base + "/" + LUID, data).get()

    def delete(self, LUID):
        request = Request(self._host_, self._port_, "DELETE", self.base + "/" + LUID).get()

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.objects = None

    def get_UID(self):
        return ""

class Request(threading.Thread, gobject.GObject):
    __gsignals__ =  { 
                    "complete": 
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_PYOBJECT])      #request,
                    }

    def __init__(self, host, port, request, URI, data=None, callback=None):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)

        self.host = host
        self.port = port
        self.request = request
        self.URI = URI
        self.in_data = data
        self.out_data = ""

        self.callback = None

    def run(self):
        conn = httplib.HTTPConnection(self.host, self.port)
        conn.request(self.request, self.URI)
        r1 = conn.getresponse()
        self.out_data = r1.read()
        conn.close()
        log(self.out_data)

        gobject.idle_add(self.emit, "complete", self)

    def get(self):
        threading.Thread.start(self)
        threading.Thread.join(self, 8)
        return self.out_data

