noinst_PROGRAMS = \
	check-libevo

common_ldflags = \
	$(top_builddir)/src/libevo.la \
	$(PACKAGE_LIBS)


check_libevo_SOURCES = check-libevo.c
check_libevo_LDADD   = $(common_ldflags) $(CHECK_LIBS)

INCLUDES = \
	-I$(top_srcdir)/src \
	$(PACKAGE_CFLAGS)

