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

import dbus.glib
import logging
log = logging.getLogger("modules.Network")

import conduit

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = ""
PROTOCOL_VERSION = "1"

PORT_IDX = 0
VERSION_IDX = 1

###
#Instead of having to depend on python-avahi we just 
#copy the functions and constants we need
###
DBUS_INTERFACE_ADDRESS_RESOLVER = 'org.freedesktop.Avahi.AddressResolver'
DBUS_INTERFACE_DOMAIN_BROWSER = 'org.freedesktop.Avahi.DomainBrowser'
DBUS_INTERFACE_ENTRY_GROUP = 'org.freedesktop.Avahi.EntryGroup'
DBUS_INTERFACE_HOST_NAME_RESOLVER = 'org.freedesktop.Avahi.HostNameResolver'
DBUS_INTERFACE_RECORD_BROWSER = 'org.freedesktop.Avahi.RecordBrowser'
DBUS_INTERFACE_SERVER = 'org.freedesktop.Avahi.Server'
DBUS_INTERFACE_SERVICE_BROWSER = 'org.freedesktop.Avahi.ServiceBrowser'
DBUS_INTERFACE_SERVICE_RESOLVER = 'org.freedesktop.Avahi.ServiceResolver'
DBUS_INTERFACE_SERVICE_TYPE_BROWSER = 'org.freedesktop.Avahi.ServiceTypeBrowser'
DBUS_NAME = 'org.freedesktop.Avahi'
DBUS_PATH_SERVER = '/'
DOMAIN_BROWSER_BROWSE = 0
DOMAIN_BROWSER_BROWSE_DEFAULT = 1
DOMAIN_BROWSER_BROWSE_LEGACY = 4
DOMAIN_BROWSER_REGISTER = 2
DOMAIN_BROWSER_REGISTER_DEFAULT = 3
ENTRY_GROUP_COLLISION = 3
ENTRY_GROUP_ESTABLISHED = 2
ENTRY_GROUP_FAILURE = 4
ENTRY_GROUP_REGISTERING = 1
ENTRY_GROUP_UNCOMMITED = 0
IF_UNSPEC = -1
LOOKUP_NO_ADDRESS = 8
LOOKUP_NO_TXT = 4
LOOKUP_RESULT_CACHED = 1
LOOKUP_RESULT_LOCAL = 8
LOOKUP_RESULT_MULTICAST = 4
LOOKUP_RESULT_OUR_OWN = 16
LOOKUP_RESULT_STATIC = 32
LOOKUP_RESULT_WIDE_AREA = 2
LOOKUP_USE_MULTICAST = 2
LOOKUP_USE_WIDE_AREA = 1
PROTO_INET = 0
PROTO_INET6 = 1
PROTO_UNSPEC = -1
PUBLISH_ALLOW_MULTIPLE = 8
PUBLISH_NO_ANNOUNCE = 4
PUBLISH_NO_COOKIE = 32
PUBLISH_NO_PROBE = 2
PUBLISH_NO_REVERSE = 16
PUBLISH_UNIQUE = 1
PUBLISH_UPDATE = 64
PUBLISH_USE_MULTICAST = 256
PUBLISH_USE_WIDE_AREA = 128
SERVER_COLLISION = 3
SERVER_FAILURE = 4
SERVER_INVALID = 0
SERVER_REGISTERING = 1
SERVER_RUNNING = 2
SERVICE_COOKIE = 'org.freedesktop.Avahi.cookie'
SERVICE_COOKIE_INVALID = 0

def byte_array_to_string(s):
    r = ""
    for c in s:
        if c >= 32 and c < 127:
            r += "%c" % c
        else:
            r += "."
    return r

def txt_array_to_string_array(t):
    l = []
    for s in t:
        l.append(byte_array_to_string(s))
    return l


def string_to_byte_array(s):
    r = []
    for c in s:
        r.append(dbus.Byte(ord(c)))
    return r

def string_array_to_txt_array(t):
    l = []
    for s in t:
        l.append(string_to_byte_array(s))
    return l

def dict_to_txt_array(txt_dict):
    l = []
    for k,v in txt_dict.items():
        l.append(string_to_byte_array("%s=%s" % (k,v)))
    return l

def txt_array_to_dict(array):
    d = {}
    for i in array:
        bits = i.split("=")
        if len(bits) == 2:
            d[bits[0]] = bits[1]
    return d

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
                            DBUS_NAME, 
                            DBUS_PATH_SERVER
                            ), 
                        DBUS_INTERFACE_SERVER
                        )

        # Get this device's hostname
        self.hostname = server.GetHostName()

        # Register this service
        path = server.EntryGroupNew()
        self.group = dbus.Interface(
                    bus.get_object(DBUS_NAME, path), 
                    DBUS_INTERFACE_ENTRY_GROUP
                    )

    def announce(self):
        """
        Resets the group, announces Conduit, and commits the change
        """
        log.debug("Announcing avahi conduit service")
        self.group.AddService(
                IF_UNSPEC,        #interface
                PROTO_UNSPEC,     #protocol
                dbus.UInt32(0),         #flags
                self.hostname,          #name
                AVAHI_SERVICE_NAME,     #service type
                AVAHI_SERVICE_DOMAIN,   #domain
                '',                     #host
                dbus.UInt16(self.port), #port
                string_array_to_txt_array([
                                "version=%s" % conduit.VERSION,
                                "protocol-version=%s" % PROTOCOL_VERSION])
                )
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
                                DBUS_NAME,
                                DBUS_PATH_SERVER),
                            DBUS_INTERFACE_SERVER)

        self.hostname = self.server.GetHostName()

        obj = bus.get_object(
                            DBUS_NAME,
                            self.server.ServiceBrowserNew(
                                IF_UNSPEC,
                                PROTO_UNSPEC,
                                AVAHI_SERVICE_NAME, 
                                AVAHI_SERVICE_DOMAIN,
                                dbus.UInt32(0)
                                )
                            )
        browser = dbus.Interface(obj, DBUS_INTERFACE_SERVICE_BROWSER)
        browser.connect_to_signal('ItemNew', self._new_service)
        browser.connect_to_signal('ItemRemove', self._remove_service)

    def _new_service(self, interface, protocol, name, type, domain, flags):
        """
        DBus callback when a new service is detected
        """
        #Dont show networked dataproviders on localhost unless we are
        #a development release
        if not conduit.IS_DEVELOPMENT_VERSION and flags & LOOKUP_RESULT_OUR_OWN:
            return

        service = self.server.ResolveService(
                                        interface, 
                                        protocol,
                                        name, 
                                        type, 
                                        domain,
                                        PROTO_UNSPEC, 
                                        dbus.UInt32(0),
                                        reply_handler = self._resolve_service, 
                                        error_handler = self._resolve_error
                                        )

    def _resolve_service(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
        """
        Dbus callback
        """
        extra_info = txt_array_to_string_array(txt)
        extra = txt_array_to_dict(extra_info)

        log.debug("Resolved conduit service %s on %s - %s:%s\nExtra Info: %s" % (name, host, address, port, extra_info))

        # Check if the service is local and then check the 
        # conduit versions are identical
        if extra.get("protocol-version", None) == PROTOCOL_VERSION:
            self.detected_cb(str(name), str(host), str(address), str(port), extra_info)
        else:
            log.debug("Ignoring %s (version: %s, protocol version: %s)" % (
                            name,
                            extra.get("version", "unknown"),
                            extra.get("protocol-version", "unknown")))

    def _remove_service(self, interface, protocol, name, type, domain, flags):
        """
        Dbus callback when a service is removed
        """
        self.removed_cb(str(name))

    def _resolve_error(self, error):
        """
        Dbus callback when a service details cannot be resolved
        """
        log.warn("Avahi/D-Bus error: %s" % repr(error))




