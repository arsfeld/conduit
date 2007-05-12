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

from twisted.web import client

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

        gobject.timeout_add(10000, self.make_one)

    def make_one(self):
        self.dataprovider_detected("Tomboy", "localhost", "Baz", "Baz", "")

    def dataprovider_detected(self, name, host, address, port, extra_info):
        """
        Callback which is triggered when a dataprovider is advertised on 
        a remote conduit instance
        """
        logd("Remote Dataprovider '%s' detected on %s" % (name, host))

        if not self.detectedHosts.has_key(host):
            self.detectedHosts[host] = {}
            self.detectedHosts[host]["category"] = DataProvider.DataProviderCategory("On %s" % host, "computer", host)

        headers = {}
        headers['Content-Type'] = None
        data = ""
        response = client.getPage("http://localhost:3400/index", method="GET", postdata=data, headers=headers)
        response.addCallback(self.process_host_xml, host)
        response.addErrback(self.process_err)

    def process_err(self, err):
        log(">>>> Network error %s" % repr(err))

    def process_host_xml(self, response, host):
        log(">>>> :O?")
        for event, elem in ET.iterparse(StringIO(response)):
            if elem.tag == "dataprovider":
                uid = elem.findtext("uid")
                name = ""
                icon = ""
                elem.clear()

                local_key = self.emit_added(
                             ClientDataProvider, 
                             (uid, name, icon), 
                             self.detectedHosts[host]["category"])

                self.detectedDataproviders[name] = {
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
    _name_ = "Networked DataProvider"
    _description_ = "Yo"
    _module_type_ = "twoway"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.objects = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.objects = []

        response = Request('localhost', 3400, "PUT", "/TomboyNoteTwoWay-None").get()
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
        response = Request('localhost', 3400, "GET", "/TomboyNoteTwoWay-None/" + uid).get()
        return None

    def put(self, data, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        response = Request('localhost', 3400, "PUT", "/TomboyNoteTwoWay-None/" + LUID, data).get()

    def delete(self, LUID):
        response = Request('localhost', 3400, "DELETE", "/TomboyNoteTwoWay-None/" + LUID).get()

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.objects = None

    def get_UID(self):
        return ""

class Request(threading.Thread):
    def __init__(self, host, port, request, URI, data=None):
        threading.Thread.__init__(self)

        self.host = host
        self.port = port
        self.request = request
        self.URI = URI
        self.in_data = data
        self.out_data = ""

    def run(self):
        conn = httplib.HTTPConnection(self.host, self.port)
        conn.request(self.request, self.URI)
        r1 = conn.getresponse()
        self.out_data = r1.read()
        logd(self.out_data)
        conn.close()
    
    def get(self):
        threading.Thread.start(self)
        threading.Thread.join(self, 8)
        return self.out_data

