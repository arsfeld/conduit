import gobject
import dbus
import dbus.glib
import avahi

AVAHI_SERVICE_NAME = "_conduit._tcp"
AVAHI_SERVICE_DOMAIN = "local"

class AvahiMonitor:
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
    print "Listening for Conduit (%s) Services" % AVAHI_SERVICE_NAME

    a = AvahiMonitor()

    try:
        gobject.MainLoop().run()
    except KeyboardInterrupt, k:
        pass         
        
