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

import avahi
import dbus, dbus.glib

import conduit

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = ""

PORT_IDX = 0
VERSION_IDX = 1

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

class AvahiAdvertiser:
    """
    Advertises the presence of dataprovider instances on the network using avahi.
    Wraps up some of the complexity due to it being hard to add additional
    services to a group once that group has been committed.
    """
    def __init__(self, name, port):
        self.name = name
        self.port = port

        # Connect to the Avahi server
        bus = dbus.SystemBus()
        server = dbus.Interface(
                        bus.get_object(
                            avahi.DBUS_NAME, 
                            avahi.DBUS_PATH_SERVER
                            ), 
                        avahi.DBUS_INTERFACE_SERVER
                        )

        # Get this device's hostname
        self.hostname = server.GetHostName()

        # Register this service
        path = server.EntryGroupNew()
        self.group = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME, path), 
                    avahi.DBUS_INTERFACE_ENTRY_GROUP
                    )

    def foo(self):
        self.group.AddServiceSubtype(
                            avahi.IF_UNSPEC,        #interface
                            avahi.PROTO_UNSPEC,     #protocol
                            0,                      #flags
                            self.hostname,          #name
                            AVAHI_SERVICE_NAME,     #service type
                            AVAHI_SERVICE_DOMAIN,   #domain
                            "_foo_"
                            )
        self.group.Commit()

    def announce(self):
        """
        Resets the group, announces Conduit, and commits the change
        """
        self.reset()

        try:
            print "-------------------------- ADDING SERVICE"
            self.group.AddService(
                    avahi.IF_UNSPEC,        #interface
                    avahi.PROTO_UNSPEC,     #protocol
                    0,                      #flags
                    self.hostname,          #name
                    AVAHI_SERVICE_NAME,     #service type
                    AVAHI_SERVICE_DOMAIN,   #domain
                    '',                     #host
                    self.port,              #port
                    avahi.string_array_to_txt_array(["version=%s" % conduit.APPVERSION])
                    )
        except dbus.DBusException, err:
            print "--------------------------------------ERROR",err

        self.group.Commit() 
            
    def reset(self):
        if not self.group.IsEmpty():
            self.group.Reset()

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
        browser.connect_to_signal('StateChanged',self.foo)

    def foo(self, *args):
        print "===========================",args

    def _new_service(self, interface, protocol, name, type, domain, flags):
        """
        DBus callback when a new service is detected
        """
        #if flags & avahi.LOOKUP_RESULT_OUR_OWN:
        #    return

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

        conduit.logd("Resolved conduit service %s on %s - %s:%s\nExtra Info: %s" % (name, host, address, port, extra_info))

        # Check if the service is local and then check the 
        # conduit versions are identical
        if extra.has_key("version") and extra["version"] == conduit.APPVERSION:
            self.detected_cb(str(name), str(host), str(address), str(port), extra_info)
        else:
            conduit.logd("Ignoring %s because remote conduit is different version" % name)

    def _remove_service(self, interface, protocol, name, type, domain, flags):
        """
        Dbus callback when a service is removed
        """
        self.removed_cb(str(name))

    def _resolve_error(self, error):
        """
        Dbus callback when a service details cannot be resolved
        """
        conduit.logw("Avahi/D-Bus error: %s" % repr(error))

