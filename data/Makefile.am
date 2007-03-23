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
# Misc data
################################################################################
resourcesdir = $(pkgdatadir)
resources_DATA = \
	conduit.glade \
	backpack.png \
	conduit-icon.png \
	conduit-splash.png \
	conflict-left.png \
	conflict-right.png \
	conflict-skip.png \
	conflict-twoway.png \
	feed-icon.png \
	f-spot.png \
	liferea.png \
	sink-icon.png \
	source-icon.png \
	tomboy.png \
	twoway-icon.png \
	conduit-progress-1.png \
	conduit-progress-2.png \
	conduit-progress-3.png \
	conduit-progress-4.png \
	conduit-progress-5.png \
	conduit-progress-6.png \
	conduit-progress-7.png \
	conduit-progress-8.png

conduitbindir = $(libdir)/conduit

################################################################################
# Desktop file
################################################################################
desktopdir = $(datadir)/applications
desktop_in_files = conduit.desktop.in 
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

################################################################################
# DBus 
################################################################################
if ENABLE_DBUS
dbusservicedir=$(DBUS_SERVICES_DIR)
dbusservice_in_files=org.gnome.Conduit.service.in
dbusservice_DATA=$(dbusservice_in_files:.service.in=.service)

$(dbusservice_DATA): $(dbusservice_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@
endif


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
	$(desktop_DATA)

EXTRA_DIST = \
	$(resources_DATA) \
	$(pkgconfig_in_files) \
	$(dbusservice_in_files) \
	conduit.desktop.in.in
	
CLEANFILES = conduit.desktop org.gnome.Conduit.service
