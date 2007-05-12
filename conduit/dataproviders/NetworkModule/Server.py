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
import conduit.Utils as Utils

import Peers

from twisted.internet import reactor
from twisted.web import resource, server

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = ""

SERVER_PORT = 3400

PORT_IDX = 0
VERSION_IDX = 1
    
class NetworkServerFactory(Module.DataProviderFactory, gobject.GObject):
    """
    Controlls all network related communication aspects. This involves
    1) Advertising dataprovider presence on local network using avahi
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

        logd(">>>> Starting NetworkServerFactory")

        if not kwargs.has_key("moduleManager"):
            return

        self.localModules = kwargs['moduleManager']

        #self.dataproviderAdvertiser = Peers.AvahiAdvertiser()
        self.advertisedDataproviders = {}

        for dp in self.localModules.get_modules_by_type(None):
            self.on_local_dataprovider_added(None, dp)

        # detect any hotpluggable dataproviders to share
        self.localModules.connect("dataprovider-added", self.on_local_dataprovider_added)
        self.localModules.connect("dataprovider-removed", self.on_local_dataprovider_removed)

        reactor.listenTCP(SERVER_PORT, server.Site(RootResource(self.localModules)))


    def on_local_dataprovider_added(self, loader, dataproviderWrapper):
        """
        When a local dataprovider is added, check it to see if it is shared then advertise it
        """
        # FIXME: Doesn't care or respect anything about the user :-)
        #if dataproviderWrapper.name == "Test Dynamic Source" or dataproviderWrapper.name == "Tomboy Notes":
        #    self.advertise_dataprovider(dataproviderWrapper)

    def on_local_dataprovider_removed(self, loader, dataproviderWrapper):
        """
        When a local dataprovider is no longer available, unadvertise it
        """
        #self.unadvertise_dataprovider(dataproviderWrapper)


    def advertise_dataprovider(self, dataproviderWrapper):
        """
        Announces the availability of the dataproviderWrapper on the network
        by selecting an allowed port and announcing as such.
        """
        logd("Advertising %s" % dataproviderWrapper)
        if not self.dataproviderAdvertiser.advertise_dataprovider(dataproviderWrapper):
            logw("Could not advertise dataprovider")

    def unadvertise_dataprovider(self, dataproviderWrapper):
        """
        Removes the advertised dataprovider and makes its port
        available to be assigned to another dataprovider later
        """
        if not dataproviderWrapper in self.advertisedDataproviders:
            return

        #Unadvertise
        self.dataproviderAdvertiser.unadvertise_dataprovider(dataproviderWrapper)

class RootResource(resource.Resource):
    def __init__(self, modules):
        resource.Resource.__init__(self)
        self.modules = modules
        self.advertised = {}

        self.putChild('index', DataproviderIndex(self.advertised))

        # look for dataproviders to share
        for dp in self.modules.get_modules_by_type(None):
            self.on_dataprovider_added(None, dp)

        # detect any hotpluggable dataproviders to share
        self.modules.connect("dataprovider-added", self.on_dataprovider_added)
        self.modules.connect("dataprovider-removed", self.on_dataprovider_removed)

    def on_dataprovider_added(self, loader, wrapper):
        # FIXME: Doesn't care or respect anything about the user :-)
        if wrapper.name == "Test Dynamic Source" or wrapper.name == "Tomboy Notes":
            instance = self.modules.get_new_module_instance(wrapper.get_key())
            self.advertised[wrapper.get_UID()] = DataproviderResource(wrapper, instance)

    def on_dataprovider_removed(self, loader, wrapper):
        if self.advertised.has_key(wrapper.get_UID()):
            del self.advertised[wrapper.get_UID()]

    def getChild(self, path, request):
        if self.advertised.has_key(path):
            return self.advertised[path]
        else:
            return self.children['index']

class DataproviderIndex(resource.Resource):
    def __init__(self, advertised):
        resource.Resource.__init__(self)
        self.advertised = advertised

    def render(self, request):
        """
        Return an XML document describing available dataproviders
        """
        #FIXME: Str concat for XML gen?? Nooooooo
        dpstr = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        dpstr += "<conduit>"
        dpstr += "<version>1</version>"
        for uid, wrapper in self.advertised.iteritems():
            dpstr += wrapper.getXML()
        dpstr += "</conduit>"
        return dpstr

class DataproviderResource(resource.Resource):
    def __init__(self, wrapper, instance):
        resource.Resource.__init__(self)
        self.wrapper = wrapper
        self.instance = instance.module
        self.objects = {}

    def get_UID(self):
        return self.wrapper.get_UID()

    def getXML(self):
        dpstr = "<dataprovider>"
        dpstr += "<uid>%s</uid>" % self.get_UID()
        dpstr += "<name>%s</name>" % self.wrapper.name
        dpstr += "<description>%s</description>" % self.wrapper.description
        dpstr += "<icon>%s</icon>" % self.wrapper.icon_name
        dpstr += "<module_type>%s</module_type>" % self.wrapper.module_type
        dpstr += "<in_type>%s</in_type>" % self.wrapper.in_type
        dpstr += "<out_type>%s</out_type>" % self.wrapper.out_type
        dpstr += "</dataprovider>"
        return dpstr

    def render(self, request):
        xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        xml += "<objects>"

        objs = {}

        # This is a bit of a fiddle until we have Conduit 0.5...
        self.instance.refresh()
        for i in range(0, self.instance.get_num_items()):
            obj = self.instance.get(i)
            obj_id = obj.get_UID()

            # cache this object 
            objs[obj_id] = obj

            # add info about this object to XML that we return
            xml += "<object><uid>%s</uid><mtime>%s</mtime></object>" % (obj_id.encode("hex"), obj.get_mtime())

        xml += "</objects>"

        self.objects = objs

        return xml

    def getChild(self, path, request):
        uid = path.decode("hex")
        if self.objects.has_key(uid):
            return DataproviderObject(self, uid)
        else:
            return self

class DataproviderObject(resource.Resource):
    def __init__(self, parent, path):
        resource.Resource.__init__(self)
        self.parent = parent
        self.path = path

    def render_GET(self, request):
        return self.parent.objects[self.path].raw
	
    def render_PUT(self, request):
        try:
            request.content.seek(0)
            data = request.content.read()

            new_uid = self.parent.instance.module.put(note, overwrite, self.path)
            return new_uid
        except:
            return "Put failed."

    def render_DELETE(self, request):
        try:
            self.parent.instance.delete(self.path)
            return "Deleted."
        except:
            return "Delete failed..."

