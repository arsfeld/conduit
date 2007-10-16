#!/usr/bin/env python
import gtk
import gtk.gdk
import gtk.glade
import gtkmozembed

win = gtk.Window()
browser = gtkmozembed.MozEmbed()
win.add(browser)
win.show_all()

gtk.main()
