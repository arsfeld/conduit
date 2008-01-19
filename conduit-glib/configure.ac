# Process this file with autoconf to produce a configure script.
# Created by Anjuta application wizard.

AC_INIT(conduit-glib, 0.2)

AM_INIT_AUTOMAKE(AC_PACKAGE_NAME, AC_PACKAGE_VERSION)
AM_CONFIG_HEADER(config.h)
AM_MAINTAINER_MODE

CFLAGS="$CFLAGS"

###################################################################
# Check essential build programs
###################################################################
AC_ISC_POSIX
AC_PROG_CC
AM_PROG_CC_STDC
AC_HEADER_STDC
AM_PROG_LIBTOOL


####################################################################
# Compiler generate debug code
####################################################################
AC_ARG_ENABLE([debug],
              AC_HELP_STRING([--enable-debug], [build with debug symbols]),,
              [enable_debug=no])

if test "x$enable_debug" = "xyes"; then
	CFLAGS="-g $CFLAGS"
fi


####################################################################
# gettext/intltool support 
####################################################################
GETTEXT_PACKAGE=AC_PACKAGE_NAME
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE,"$GETTEXT_PACKAGE",
                   [The gettext translation domain])

AM_GLIB_GNU_GETTEXT
IT_PROG_INTLTOOL([0.35.0])


####################################################################
# Check library deps
####################################################################
GLIB_REQUIRED=2.12
DBUS_GLIB_REQUIRED=0.73
DBUS_REQUIRED=1.0.0

#PKG_CHECK_MODULES(CONDUIT_GLIB, [glib-2.0 >= $GLIB_REQUIRED dbus-glib-1 >= DBUS_GLIB_REQUIRED dbus-1 >= $DBUS_REQUIRED gobject-2.0 >= GLIB_REQUIRED ])
PKG_CHECK_MODULES(GLIB2, [glib-2.0 >= $GLIB_REQUIRED ])
PKG_CHECK_MODULES(GOBJECT2, [gobject-2.0 >= $GLIB_REQUIRED ])
PKG_CHECK_MODULES(DBUS_GLIB, [dbus-glib-1 >= $DBUS_GLIB_REQUIRED ])
PKG_CHECK_MODULES(DBUS, [dbus-1 >= $DBUS_REQUIRED ])

CONDUIT_GLIB_CFLAGS="$GLIB2_CFLAGS $GOBJECT2_CFLAGS $DBUS_GLIB_CFLAGS $DBUS_CFLAGS"
CONDUIT_GLIB_LIBS="$GLIB2_LIBS $GOBJECT2_LIBS $DBUS_GLIB_LIBS $DBUS_LIBS"
AC_SUBST(CONDUIT_GLIB_CFLAGS)
AC_SUBST(CONDUIT_GLIB_LIBS)


GTK_DOC_CHECK(1.0)


####################################################################
# check for newer glib (>= 2.15.0) for unit testing framework
####################################################################
RECENT_GLIB=2.15.0

PKG_CHECK_MODULES(glib2, [ glib-2.0 >= $RECENT_GLIB ],
                  [have_recent_glib=yes], [have_recent_glib=no])

if test "$have_recent_glib" = "yes" ; then
   AC_DEFINE(HAVE_RECENT_GLIB, 1, [Define if we have recent glib])
fi

AM_CONDITIONAL(HAVE_RECENT_GLIB, test "$have_recent_glib" = "yes")


AC_OUTPUT([
conduit-glib.pc
Makefile
po/Makefile.in
test/Makefile
data/Makefile
docs/Makefile
docs/reference/Makefile
conduit-glib/Makefile
])
