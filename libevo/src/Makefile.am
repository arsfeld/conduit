evoincdir = $(includedir)/libevo

lib_LTLIBRARIES = libevo.la

evoinc_HEADERS = \
	evo-environment.h \
	evo-addressbook.h \
	evo-contact.h 

libevo_la_SOURCES = \
	evo-environment.c \
	evo-addressbook.c \
	evo-contact.c 

libevo_la_LIBADD = $(PACKAGE_LIBS)

INCLUDES = \
	-I$(top_srcdir) \
	$(PACKAGE_CFLAGS)

