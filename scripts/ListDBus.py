#!/usr/bin/python
import dbus
obj = dbus.SessionBus().get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
avail = dbus_iface.ListNames()

for a in avail:
    print a


