SUBDIRS = icons

################################################################################
# Package Config Stuff
################################################################################
pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_in_files = conduit.pc.in
pkgconfig_DATA = $(pkgconfig_in_files:.pc.in=.pc)

################################################################################
# GConf Schemas
################################################################################
# GConf Preference Schemas
#schemadir = $(GCONF_SCHEMA_FILE_DIR)
#schema_in_files = conduit.schemas.in
#schema_DATA = $(schema_in_files:.schemas.in=.schemas)
#@INTLTOOL_SCHEMAS_RULE@

################################################################################
# Icons
################################################################################
install-data-hook: update-icon-cache
uninstall-hook: update-icon-cache
update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk icon cache."; \
		$(gtk_update_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After (un)install, run this:"; \
		echo "***   $(gtk_update_icon_cache)"; \
	fi

resourcesdir = $(pkgdatadir)
resources_DATA = \
	conduit.glade \
	backpack.png \
	conduit-splash.png \
	feed.png \
	f-spot.png \
	liferea.png \
	tomboy.png \
	picasa.png \
	smugmug.png \
	boxdotnet.png \
	flickr.png

conduitbindir = $(libdir)/conduit

################################################################################
# Desktop and autostart file
################################################################################
desktopdir = $(datadir)/applications
desktop_in_files = conduit.desktop.in 
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

autostartdir = $(datadir)/gnome/autostart
autostart_in_files = conduit-autostart.desktop.in
autostart_DATA = $(autostart_in_files:.desktop.in=.desktop)

@INTLTOOL_DESKTOP_RULE@

################################################################################
# DBus 
################################################################################
dbusservicedir=$(DBUS_SERVICES_DIR)
dbusservice_in_files=org.gnome.Conduit.service.in
dbusservice_DATA=$(dbusservice_in_files:.service.in=.service)

$(dbusservice_DATA): $(dbusservice_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

################################################################################
# Build rules
################################################################################
#if GCONF_SCHEMAS_INSTALL
#install-data-local: install-schemas
#install-schemas:
#	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
#		$(GCONFTOOL) --makefile-install-rule $(schema_DATA)
#endif

DISTCLEANFILES = \
	$(pkgconfig_DATA) \
	$(desktop_DATA) \
	$(autostart_DATA)

EXTRA_DIST = \
	$(resources_DATA) \
	$(pkgconfig_in_files) \
	$(dbusservice_in_files) \
	conduit.desktop.in.in \
	conduit-autostart.desktop.in.in
	
CLEANFILES = conduit.desktop org.gnome.Conduit.service
