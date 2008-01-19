## Process this file with automake to produce Makefile.in

SUBDIRS =           \
	conduit-glib    \
    docs            \
    data            \
	po              \
	test

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = conduit-glib.pc

conduit_glibdocdir = ${prefix}/doc/conduit-glib

conduit_glibdoc_DATA = \
	README   \
	COPYING  \
	AUTHORS  \
	INSTALL  \
    MAINTAINERS

EXTRA_DIST = \
	intltool-extract.in \
	intltool-merge.in   \
	intltool-update.in  \
    conduit-glib.pc.in	\
	TODO.tasks          \
    conduit-glib.anjuta   \
    $(conduit_glibdoc_DATA)

DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

DISTCHECK_CONFIGURE_FLAGS = --enable-gtk-doc


