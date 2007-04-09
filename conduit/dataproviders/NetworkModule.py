"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Parts of this code adapted from glchess (GPLv2)
http://glchess.sourceforge.net/
Parts of this code adapted from elisa (GPLv2)


Copyright: John Stowers, 2006
License: GPLv2
"""

import gobject
import avahi
import dbus
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import conduit
from conduit import log,logd,logw
from conduit.ModuleWrapper import ModuleWrapper
import conduit.Module as Module
import conduit.DataProvider as DataProvider

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = ""
ALLOWED_PORT_FROM = 3400
ALLOWED_PORT_TO = 3410

PORT_IDX = 0
VERSION_IDX = 1

#MODULES = {
#        "NetworkFactory" :     { "type": "dataprovider-factory" }
#}

def decode_avahi_text_array_to_dict(array):
    """
    Avahi text arrays are encoded as key=value
    This function converts the array to a dict
    """
    d = {}
    for i in array:
        bits = i.split("=")
        if len(bits) == 2:
            d[bits[0]] = bits[1]
    return d

def encode_dict_to_avahi_text_array(d):
    """
    Encodes a python dict to the 'key=value' format expected
    by avahi
    """
    array = []
    for key in d:
        array.append("%s=%s" % (key, d[key]))
    return array
    
class NetworkFactory(Module.DataProviderFactory, gobject.GObject):
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

        self.dataproviderAdvertiser = AvahiAdvertiser()
        self.advertisedDataproviders = {}

        self.dataproviderMonitor = AvahiMonitor(self.dataprovider_detected, self.dataprovider_removed)
        self.detectedHosts = {}
        self.detectedDataproviders = {}

        #Keep record of advertised dataproviders
        #Keep record of which ports are already used
        self.usedPorts = {}
        for i in range(ALLOWED_PORT_FROM, ALLOWED_PORT_TO):
            self.usedPorts[i] = False

        # look for dataproviders to share
        for dp_type in ["twoway", "sink", "source"]:
            for dp in self.localModules.get_modules_by_type(dp_type):
                self.on_local_dataprovider_added(None, dp)

        # detect any hotpluggable dataproviders to share
        self.localModules.connect("dataprovider-added", self.on_local_dataprovider_added)
        self.localModules.connect("dataprovider-removed", self.on_local_dataprovider_removed)

    def on_local_dataprovider_added(self, loader, dataproviderWrapper):
        """
        When a local dataprovider is added, check it to see if it is shared then advertise it
        """
        # FIXME: Doesn't care or respect anything about the user :-)
        if dataproviderWrapper.name == "Test Dynamic Source" or dataproviderWrapper.name == "Tomboy Notes":
            self.advertise_dataprovider(dataproviderWrapper)

    def on_local_dataprovider_removed(self, loader, dataproviderWrapper):
        """
        When a local dataprovider is no longer available, unadvertise it
        """
        self.unadvertise_dataprovider(dataproviderWrapper)

    def advertise_dataprovider(self, dataproviderWrapper):
        """
        Announces the availability of the dataproviderWrapper on the network
        by selecting an allowed port and announcing as such.
        """
        port = None
        for i in range(ALLOWED_PORT_FROM, ALLOWED_PORT_TO):
            if self.usedPorts[i] == False:
                port = i
                break
        
        if port != None:
            logd("Advertising %s on port %s" % (dataproviderWrapper, port))
            ok = self.dataproviderAdvertiser.advertise_dataprovider(dataproviderWrapper, port)
            if ok:
                self.advertisedDataproviders[dataproviderWrapper] = port
                self.usedPorts[port] = True
            else:
                logw("Could not advertise dataprovider")
        else:
            logw("Could not find free a free port to advertise %s" % dataproviderWrapper)

    def unadvertise_dataprovider(self, dataproviderWrapper):
        """
        Removes the advertised dataprovider and makes its port
        available to be assigned to another dataprovider later
        """
        
        if not dataproviderWrapper in self.advertisedDataproviders:
            return

        #Look up the port, remove it from the list of used ports
        port = self.advertisedDataproviders[dataproviderWrapper]
        self.usedPorts[port] = False

        #Unadvertise
        self.dataproviderAdvertiser.unadvertise_dataprovider(dataproviderWrapper)

    def dataprovider_detected(self, name, host, address, port, extra_info):
        """
        Callback which is triggered when a dataprovider is advertised on 
        a remote conduit instance
        """
        logd("Remote Dataprovider '%s' detected on %s" % (name, host))

        if not self.detectedHosts.has_key(host):
            self.detectedHosts[host] = {}
            self.detectedHosts[host]["category"] = DataProvider.DataProviderCategory("On %s" % host, "computer", host)

        #FIXME: Do more than emite a dummy dp!!
        local_key = self.emit_added(
                             RemoteDataProvider, 
                             (name, host, port), 
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

class RemoteDataProvider(DataProvider.TwoWay):
    _name_ = "Networked DataProvider"
    _description_ = "Yo"
    _module_type_ = "twoway"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.data = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.data = [1,2,3,4,5]

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.data)

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        return self.data[index]

    def put(self, data, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        return "2384987397429834"

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.data = None

class RemoteModuleWrapper(ModuleWrapper):
    """
    A DataProviderWrapper but running on another machine. Intercepts 
    calls to .module.foo() functions and calls these over RPC to the 
    remote module instead.
    """
    def __init__(self, classname, host, address, port):
        pass

class AvahiAdvertiser:
    """
    Advertises the presence of dataprovider instances on the network using avahi.
    Wraps up some of the complexity due to it being hard to add additional
    services to a group once that group has been committed.

    Code adapted from glchess

    Each advertised dataprovider is given its own service. This done for 
    several reasons.
    1) Each dataprovider that is advertised is given its own port. Because
    subservices cannot specify a port (or a txt variable into which a port may
    be encoded) i encode the hostname in the advertised service to form some
    sort of namespacing.
    e.g.    hostname:advertisedDataProvider1
            hostname:advertisedDataProvider2
            hostname2:advertisedDataProvider1
    2) I could have encoded all of the advertised services in the
    txtdata field of the sercice. However it is easier to have one callback 
    for ItemNew than it is to have seperate callbacks for New Item, and when the
    textdata changes. Furthurmore I want each dataprovider to be on its own
    port so being limited to one service and port is a disadvantage here    
    """
    def __init__(self):
        """
        Constructor.
        """
        #Maintain a list of currently advertised dataproviders
        self.advertisedDataProviders = {}

        # Connect to the Avahi server
        bus = dbus.SystemBus()
        server = dbus.Interface(
                        bus.get_object(
                            avahi.DBUS_NAME, 
                            avahi.DBUS_PATH_SERVER
                            ), 
                        avahi.DBUS_INTERFACE_SERVER
                        )
        self.hostname = server.GetHostName()
        # Register this service
        path = server.EntryGroupNew()
        self.group = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME, path), 
                    avahi.DBUS_INTERFACE_ENTRY_GROUP
                    )

    def _add_service(self, name, port, version):
        """
        Adds the service representing a dataprovider
        to the group
        """
        try:
            self.group.AddService(
                    avahi.IF_UNSPEC,        #interface
                    avahi.PROTO_UNSPEC,     #protocol
                    0,                      #flags
                    "%s:%s" % (self.hostname,name),     #name
                    AVAHI_SERVICE_NAME,     #service type
                    AVAHI_SERVICE_DOMAIN,   #domain
                    '',                     #host
                    port,                   #port
                    avahi.string_array_to_txt_array(["version=%s" % version])
                    )
        except dbus.DBusException, err:
            print err            

    def _advertise_all_services(self):
        """
        Resets the group, advertises all services, and commits the change
        """
        self._reset_all_services()
        for name in self.advertisedDataProviders:
            port = self.advertisedDataProviders[name][PORT_IDX]
            version = self.advertisedDataProviders[name][VERSION_IDX]
            self._add_service(name, port, version)
        self._commit_all_services()
            
    def _reset_all_services(self):
        if not self.group.IsEmpty():
            self.group.Reset()

    def _commit_all_services(self):
        self.group.Commit()
        
    def advertise_dataprovider(self, dataproviderWrapper, port):
        """
        Advertises the dataprovider on the local network. Returns true if the
        dataprovider is successfully advertised.

        @returns: True if the dataprovder is successfully advertised
        @rtype:C{bool}
        """
        name = dataproviderWrapper.get_key()
        version = conduit.APPVERSION
        if name not in self.advertisedDataProviders:
            #add the new service to the list to be advertised
            self.advertisedDataProviders[name] = (port, version)
            #re-advertise all services
            self._advertise_all_services()
            return True
        return False            

    def unadvertise_dataprovider(self, dataproviderWrapper):
        """
        Unadvertises the dataprovider on the local network.
        """
        name = dataproviderWrapper.get_key()
        if name in self.advertisedDataProviders:
            #Remove the old service to the list to be advertised
            del(self.advertisedDataProviders[name])
            #re-advertise all services
            self._advertise_all_services()

    def get_advertised_dataprovider_port(self, dataproviderWrapper):
        """
        Returns the port on which the dataprovider is advertised
        @returns: Port number
        @rtype: C{int}
        """
        name = dataproviderWrapper
        return self.advertisedDataProviders[name][PORT_IDX]

class AvahiMonitor:
    """
    Watches the network for other conduit instances using avahi.

    Code adapted from elisa
    """
    def __init__(self, dataprovider_detected_cb, dataprovider_removed_cb):
        """
        Connects to the system bus and configures avahi to listen for
        Conduit services
        """
        #Callbacks fired when a conduit dataprovider is detected
        self.detected_cb = dataprovider_detected_cb
        self.removed_cb = dataprovider_removed_cb

        bus = dbus.SystemBus()
        self.server = dbus.Interface(
                            bus.get_object(
                                avahi.DBUS_NAME,
                                avahi.DBUS_PATH_SERVER),
                            avahi.DBUS_INTERFACE_SERVER)
        self.hostname = self.server.GetHostName()
        obj = bus.get_object(
                            avahi.DBUS_NAME,
                            self.server.ServiceBrowserNew(
                                avahi.IF_UNSPEC,
                                avahi.PROTO_UNSPEC,
                                AVAHI_SERVICE_NAME, 
                                AVAHI_SERVICE_DOMAIN,
                                dbus.UInt32(0)
                                )
                            )
        browser = dbus.Interface(obj, avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        browser.connect_to_signal('ItemNew', self._new_service)
        browser.connect_to_signal('ItemRemove', self._remove_service)

    def _new_service(self, interface, protocol, name, type, domain, flags):
        """
        DBus callback when a new service is detected
        """
        if flags & avahi.LOOKUP_RESULT_OUR_OWN:
            return

        service = self.server.ResolveService(
                                        interface, 
                                        protocol,
                                        name, 
                                        type, 
                                        domain,
                                        avahi.PROTO_UNSPEC, 
                                        dbus.UInt32(0),
                                        reply_handler = self._resolve_service, 
                                        error_handler = self._resolve_error
                                        )

    def _resolve_service(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
        """
        Dbus callback
        """
        extra_info = avahi.txt_array_to_string_array(txt)
        extra = decode_avahi_text_array_to_dict(extra_info)

        logd("Resolved conduit service %s on %s - %s:%s\nExtra Info: %s" % (name, host, address, port, extra_info))

        # Check if the service is local and then check the 
        # conduit versions are identical
        if extra.has_key("version") and extra["version"] == conduit.APPVERSION:
            self.detected_cb(str(name), str(host), str(address), str(port), extra_info)
        else:
            logd("Ignoring %s because remote conduit is different version" % name)

    def _remove_service(self, interface, protocol, name, type, domain, flags):
        """
        Dbus callback when a service is removed
        """
        self.removed_cb(str(name))

    def _resolve_error(self, error):
        """
        Dbus callback when a service details cannot be resolved
        """
        logw("Avahi/D-Bus error: %s" % repr(error))


################################################################################
# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/457669
################################################################################
