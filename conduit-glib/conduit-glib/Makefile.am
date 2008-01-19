## Process this file with automake to produce Makefile.in

## Created by Anjuta

INCLUDES = \
	-DPACKAGE_LOCALE_DIR=\""$(prefix)/$(DATADIRNAME)/locale"\" \
	-DPACKAGE_SRC_DIR=\""$(srcdir)"\" \
	-DPACKAGE_DATA_DIR=\""$(datadir)"\" \
    -I$(top_srcdir) -I$(srcdir) 	\
	$(CONDUIT_GLIB_CFLAGS)

AM_CFLAGS =\
	 -Wall\
	 -g

#
# Headers to be installed
#
devel_headers_HEADERS =         \
	conduit-g-application.h     \
    conduit-glib.h

#
# Path to install headers in
#
devel_headersdir = $(includedir)/conduit-glib

lib_LTLIBRARIES = \
	libconduit-glib.la

EXTRA_DIST=conduit-marshal.list

BUILT_SOURCES = \
	conduit-marshal.c                   \
    conduit-marshal.h		            \
    conduit-application-bindings.h      \
    conduit-dataprovider-bindings.h     \
    conduit-conduit-bindings.h          \
    conduit-syncset-bindings.h

libconduit_glib_la_SOURCES =            \
	conduit-g-application.c             \
	conduit-g-application.h             \
	conduit-g-dataprovider.c            \
	conduit-g-dataprovider.h            \
	conduit-g-conduit.c                 \
	conduit-g-conduit.h                 \
	conduit-g-syncset.c                 \
	conduit-g-syncset.h                 \
	conduit-glib-globals.h              \
	conduit-glib.h                      \
	$(BUILT_SOURCES)


libconduit_glib_la_LIBADD = \
	$(conduit_GLIB_LIBS)

conduit-marshal.h: conduit-marshal.list
	glib-genmarshal --header --prefix=conduit_marshal $< > conduit-marshal.h

conduit-marshal.c: conduit-marshal.list
	glib-genmarshal --body --prefix=conduit_marshal $< > conduit-marshal.c

conduit-%-bindings.h: $(top_srcdir)/data/%.xml
	dbus-binding-tool --mode=glib-client --output=$@ --prefix=$(subst -,_,$*) $^

CLEANFILES = $(BUILT_SOURCES)

