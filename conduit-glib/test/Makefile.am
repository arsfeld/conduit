noinst_PROGRAMS =       \
	test-application

INCLUDES =                                                              \
        -I$(top_srcdir) -I$(srcdir) 	                                \
        -DPACKAGE_LOCALE_DIR=\""$(prefix)/$(DATADIRNAME)/locale"\"      \
        -DPACKAGE_SRC_DIR=\""$(srcdir)"\"                               \
        -DPACKAGE_DATA_DIR=\""$(datadir)"\" $(CONDUIT_GLIB_CFLAGS)

AM_CFLAGS = \
	 -Wall  \
	 -g

test_application_SOURCES = test-application.c
test_application_LDADD = $(CONDUIT_GLIB_LIBS) $(top_builddir)/conduit-glib/libconduit-glib.la



