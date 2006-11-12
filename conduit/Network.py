"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Parts of this code adapted from glchess (GPLv2)
http://glchess.sourceforge.net/
Parts of this code adapted from elisa (GPLv2)


Copyright: John Stowers, 2006
License: GPLv2
"""

#Hack when run from command line
try:
    import conduit
    import logging
except:
    pass

import avahi
import dbus

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = "local"
ALLOWED_PORT_FROM = 3400
ALLOWED_PORT_TO = 3410

PORT_IDX = 0
VERSION_IDX = 1

class ConduitNetworkManager:
    """
    Controlls all network related communication aspects. This involves
    1) Advertising dataprovider presence on local network using avahi
    2) Discovering remote conduit capabilities (i.e. what dataproviders it has advertised)
    3) Data transmission to/from remote conduit instances
    """
    def __init__(self):
        self.dataproviderAdvertiser = AvahiAdvertiser()
        #self.dataproviderMonitor = AvahiMonitor()
        self.detectedConduits = {}

        #Keep record of which ports are already used
        self.usedPorts = {}
        for i in range(ALLOWED_PORT_FROM, ALLOWED_PORT_TO):
            self.usedPorts[i] = False

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
            logging.debug("Advertising %s on port %s" % (dataproviderWrapper, port))
            self.dataproviderAdvertiser.advertise_dataprovider(dataproviderWrapper, port)
            self.usedPorts[port] = True
        else:
            logging.warn("Could not find free a free port to advertise %s" % dataproviderWrapper)

    def unadvertise_dataprovider(self, dataproviderWrapper):
        #Look up the port, remove it from the list of used ports
        port = self.dataproviderAdvertiser.get_advertised_dataprovider_port(dataproviderWrapper)
        self.usedPorts[port] = False
        #Unadvertise
        self.dataproviderAdvertiser.unadvertise_dataprovider(dataproviderWrapper)

class RemoteDataProvider:
    """
    A DataProviderWrapper but running on another machine
    """
    def __init__(self, className, hostName, hostAddress, hostPort):
        """
        """
        self.className = className
        self.hostName = hostName
        self.hostAddress = hostAddress
        self.hostPort = hostPort

class AvahiAdvertiser:
    """
    Advertises the presence of dataprovider instances on the network using avahi.
    Wraps up some of the complexity due to it being hard to add additional
    services to a group once that group has been committed

    Code adapted from glchess
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
                    name,                   #name
                    AVAHI_SERVICE_NAME,     #service type
                    AVAHI_SERVICE_DOMAIN,   #domain
                    '',                     #host
                    port,                   #port
                    avahi.string_array_to_txt_array(["version=%s" % version])
                    )
        except dbus.dbus_bindings.DBusException, err:
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
        name = dataproviderWrapper
        version = conduit.APPVERSION
        if name not in self.advertisedDataProviders:
            #add the new service to the list to be advertised
            self.advertisedDataProviders[name] = (port, version)
            #re-advertise all services
            self._advertise_all_services()
            
    def unadvertise_dataprovider(self, dataproviderWrapper):
        name = dataproviderWrapper
        if name in self.advertisedDataProviders:
            #Remove the old service to the list to be advertised
            del(self.advertisedDataProviders[name])
            #re-advertise all services
            self._advertise_all_services()

    def get_advertised_dataprovider_port(self, dataproviderWrapper):
        name = dataproviderWrapper
        return self.advertisedDataProviders[name][PORT_IDX]

class AvahiMonitor:
    """
    Watches the network for other conduit instances using avahi.

    Code adapted from elisa
    """
    def __init__(self):
        """
        Connects to the system bus and configures avahi to listen for
        Conduit services
        """
        bus = dbus.SystemBus()
        self.server = dbus.Interface(
                            bus.get_object(
                                avahi.DBUS_NAME,
                                avahi.DBUS_PATH_SERVER),
                            avahi.DBUS_INTERFACE_SERVER)
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
        print "NEW SERVICE"
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
        print "RESOLVED SERVICE %s on %s - %s:%s\nExtra Info: %s" % (name, host, address, port, extra_info)

    def _remove_service(self, interface, protocol, name, type, domain, flags):
        """
        Dbus callback when a service is removed
        """
        print "REMOVED SERVICE"

    def _resolve_error(self, error):
        """
        Dbus callback when a service details cannot be resolved
        """
        print 'Avahi/D-Bus error: ' + repr(error)

if __name__ == "__main__":
    import gobject

    print "Listening for Conduit (%s) Services" % AVAHI_SERVICE_NAME

    a = AvahiMonitor()

    try:
        gobject.MainLoop().run()
    except KeyboardInterrupt, k:
        pass         
        

################################################################################
# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/457669
################################################################################
