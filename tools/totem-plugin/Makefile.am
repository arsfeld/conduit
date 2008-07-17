plugin_in_files = conduit.totem-plugin.in

if ENABLE_TOTEM_PLUGIN
plugindir = $(TOTEM_PLUGIN_DIR)/conduit
plugin_PYTHON = conduit.py

%.totem-plugin: %.totem-plugin.in $(INTLTOOL_MERGE) $(wildcard $(top_srcdir)/po/*po) ; $(INTLTOOL_MERGE) $(top_srcdir)/po $< $@ -d -u -c $(top_builddir)/po/.intltool-merge-cache

plugin_DATA = $(plugin_in_files:.totem-plugin.in=.totem-plugin)

CLEANFILES = $(plugin_DATA)
DISTCLEANFILES = $(plugin_DATA)
endif

EXTRA_DIST = $(plugin_in_files) conduit.py
