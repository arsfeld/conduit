"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Parts of this code adapted from glchess (GPLv2)
http://glchess.sourceforge.net/
Parts of this code adapted from elisa (GPLv2)
Parts of this code adapted from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/457669

Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject

import conduit
from conduit import log,logd,logw
from conduit.ModuleWrapper import ModuleWrapper
import conduit.Module as Module
import conduit.DataProvider as DataProvider

import copy
import httplib
from cStringIO import StringIO
try:
    import xml.etree.ElementTree as ET
except:
    import elementtree.ElementTree as ET

import threading

class NetworkClientFactory(Module.DataProviderFactory, gobject.GObject):
    """
    Controlls all network related communication aspects. This involves
    1) Advertising dataprovider presence on local network using avahi
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

        if not kwargs.has_key("moduleManager"):
            return

        self.localModules = kwargs['moduleManager']

#        self.dataproviderMonitor = Peers.AvahiMonitor(self.dataprovider_detected, self.dataprovider_removed)
        self.detectedHosts = {}
        self.detectedDataproviders = {}

        gobject.timeout_add(1000, self.make_one)

    def make_one(self):
        self.dataprovider_detected("Tomboy", "localhost", "Baz", 3400, "")

    def dataprovider_detected(self, name, host, address, port, extra_info):
        """
        Callback which is triggered when a dataprovider is advertised on 
        a remote conduit instance
        """
        logd("Remote Dataprovider '%s' detected on %s" % (name, host))

        if not self.detectedHosts.has_key(host):
            self.detectedHosts[host] = {}
            self.detectedHosts[host]["category"] = DataProvider.DataProviderCategory("On %s" % host, "computer", host)

        request = Request(host, port, "GET", "/")
        request.connect("complete", self.process_host_xml)
        request.start()

    def process_host_xml(self, huh, response):
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
                         }

                new_dp = type(guid, (ClientDataProvider, ), params)

                elem.clear()

                local_key = self.emit_added(
                             new_dp, 
                             (new_dp._host_, ), 
                             self.detectedHosts[response.host]["category"])

                self.detectedDataproviders[guid] = {
                                                   "local_key" : local_key,
                                                   }

    def dataprovider_removed(self, name):
        """
        Callback which is triggered when a dataprovider is unadvertised 
        from a remote conduit instance
        """
        if self.detectedDataproviders.has_key(name):
            logd("Remote Dataprovider '%s' removed" % name)

            self.emit_removed(self.detectedDataproviders[name]['local_key'])
            del self.detectedDataproviders[name]

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

