#!/usr/bin/python
import dbus
from xml.dom import minidom

obj = dbus.SessionBus().get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
avail = dbus_iface.ListNames()

print "AVAILABLE SERVICES:"
for a in avail:
    print "\t%s" % a
print ""

inspect={
    "org.gnome.Conduit":["/","/activate"],
    "org.gnome.Tomboy":["/org/gnome/Tomboy/RemoteControl"],
    "org.gnome.Banshee":["/org/gnome/Banshee/Player"],
    }
      

def enumerate_interface(service, interface):
    print "ENUMERATING %s:%s" % (service,interface)

    obj = dbus.SessionBus().get_object(service, interface) 
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Introspectable')
    rawxml = iface.Introspect()
    print rawxml

for service in inspect:
#    if service in avail:
        print "################################################################"
        print "# ENUMERATING %s " % service
        print "################################################################"
        for interface in inspect[service]:
            enumerate_interface(service, interface)

