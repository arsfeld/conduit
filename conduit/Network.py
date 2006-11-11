"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Parts of this code adapted from glchess (GPLv2)
http://glchess.sourceforge.net/

Copyright: John Stowers, 2006
License: GPLv2
"""

#import conduit
#import logging

import avahi
import dbus

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = "local"

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
        self.reporter = DataProviderReporter()
        self.detectedConduits = {}

    def advertise_dataprovider(self, dataproviderWrapper):
        """
        Announces the availability of the dataproviderWrapper on the network
        by selecting am allowed port and announcing as such
        """
        port = 3405
        self.reporter.advertise_dataprovider(dataproviderWrapper, port)

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

class DataProviderReporter:
    """
    Reports the presence of dataprovider instances on the network using avahi.
    Wraps up some of the complexity due to it being hard to add additional
    services to a group once that group has been committed
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
                    avahi.string_array_to_txt_array(['version='])
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
        version = "234"
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

import gobject

if __name__ == "__main__":
    print "Running"

    c = ConduitNetworkManager()
    c.advertise_dataprovider("foo")
    c.advertise_dataprovider("bar")

    try:
        gobject.MainLoop().run()
    except KeyboardInterrupt, k:
        pass


################################################################################
# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/457669
################################################################################
