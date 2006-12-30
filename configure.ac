AC_INIT(conduit, 0.3.0, john.stowers@gmail.com)
AC_CONFIG_SRCDIR(conduit/__init__.py)
AC_CONFIG_HEADERS(config.h)
AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE
GNOME_COMMON_INIT

AM_MAINTAINER_MODE
AM_DISABLE_STATIC
AM_PROG_LIBTOOL
AC_SUBST(ACLOCAL_AMFLAGS, "$ACLOCAL_FLAGS -I m4")
AC_PROG_CC

dnl ****************************************************************************
dnl * Pkg-Config
dnl ****************************************************************************
AC_CHECK_PROG(HAVE_PKGCONFIG, pkg-config, yes, no)
if test "x$HAVE_PKGCONFIG" = "xno"; then
  AC_MSG_ERROR(you need to have pkgconfig installed !)
fi

dnl ****************************************************************************
dnl * Translation & i18n
dnl ****************************************************************************
GETTEXT_PACKAGE="conduit"
IT_PROG_INTLTOOL([0.35.0])
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])
AM_GLIB_GNU_GETTEXT

dnl ****************************************************************************
dnl * DISABLED Gnome Doc Utils
dnl ****************************************************************************
dnl GNOME_DOC_INIT

dnl ****************************************************************************
dnl * DISABLED GConf support
dnl ****************************************************************************
dnl AC_PATH_PROG(GCONFTOOL, gconftool-2)
dnl AM_GCONF_SOURCE_2

dnl ****************************************************************************
dnl * Python 2.4
dnl ****************************************************************************
AM_PATH_PYTHON(2.4)
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

dnl ****************************************************************************
dnl * Write the values of various paths in defs.py
dnl ****************************************************************************
AC_SUBST(VERSION)
AC_SUBST(PACKAGE)

AS_AC_EXPAND(DATADIR, $datarootdir)
AC_SUBST(DATADIR)

AS_AC_EXPAND(PKGDATADIR, $datarootdir/$PACKAGE)
AC_SUBST(PKGDATADIR)

AS_AC_EXPAND(ICONDIR, $datarootdir/$PACKAGE/icons)
AC_SUBST(ICONDIR)

AS_AC_EXPAND(LIBDIR, $libdir)
AC_SUBST(LIBDIR)

AS_AC_EXPAND(PKGLIBDIR, $libdir/$PACKAGE)
AC_SUBST(PKGLIBDIR)

AS_AC_EXPAND(PYTHONDIR, $pythondir)
AC_SUBST(PYTHONDIR)
		
dnl ****************************************************************************
dnl * PyGTK & co for Gnome Streamer
dnl ****************************************************************************
PKG_CHECK_MODULES(CONDUIT,
	gtk+-2.0				>= 2.10
	pygtk-2.0				>= 2.10
	pygobject-2.0			>= 2.6
)
AC_SUBST(CONDUIT_CFLAGS)
AC_SUBST(CONDUIT_LIBS)

dnl ****************************************************************************
dnl * DISABLED Check for things in contrib
dnl ****************************************************************************
dnl AC_MSG_CHECKING([for FIXME module])
dnl if AC_RUN_LOG([$PYTHON -c '
dnl try:
dnl     import gnomeapplet
dnl except ImportError, e:
dnl     if str(e).find("FIXME") >= 0:
dnl           raise
dnl except:
dnl     pass
dnl ']); then
dnl   AC_MSG_RESULT([yes])
dnl else
dnl   AC_MSG_RESULT([no])
dnl   AC_MSG_ERROR([FIXME Python module required to build conduit])
dnl fi

dnl ****************************************************************************
dnl * Check for evolution's libebook to build the evolution handler
dnl ****************************************************************************
AC_ARG_ENABLE(evolution,
	AC_HELP_STRING([--disable-evolution], [Disable evolution's libebook support (default auto)]),
	enable_libebook=$enableval,
	enable_libebook=auto)

PKG_CHECK_MODULES(EVOLUTION,
	libebook-1.2			>= 1.7.92
	libecal-1.2
	gtk+-2.0				>= 2.6
	gdk-pixbuf-2.0
	pango
	pygtk-2.0				>= 2.6
	pygobject-2.0			>= 2.6,
	have_libebook_dependencies=yes,
	have_libebook_dependencies=no)

if test "x$have_libebook_dependencies" = "xno"; then
	dnl error out if user has explicitly requested libebook
	if test "x$enable_libebook" = "xyes"; then
		AC_MSG_ERROR([Could not find evolution's libebook])
	fi
	enable_libebook="no (missing dependencies)"
else
	if test "x$enable_libebook" != "xno"; then
		enable_libebook="yes"
	else
		enable_libebook="no (disabled)"
	fi
fi
AM_CONDITIONAL(ENABLE_EVOLUTION, test "x$enable_libebook" = "xyes")
AC_SUBST(EVOLUTION_LIBS)
AC_SUBST(EVOLUTION_CFLAGS)

dnl ****************************************************************************
dnl * PyGTK Codegen and defs files
dnl ****************************************************************************
AC_PATH_PROG(PYGTK_CODEGEN, pygtk-codegen-2.0, no)
if test "x$PYGTK_CODEGEN" = xno; then
  AC_MSG_ERROR(could not find pygtk-codegen-2.0 script)
fi

AC_MSG_CHECKING(for pygtk defs)
PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)
AC_MSG_RESULT($PYGTK_DEFSDIR)

dnl ****************************************************************************
dnl * DISABLED Check for prctl()
dnl ****************************************************************************
dnl AC_CHECK_FUNC(prctl, HAVE_PRCTL="yes", HAVE_PRCTL="yes")
dnl if test "x$HAVE_PRCTL" = "xyes"; then
dnl 	AC_CHECK_DECL(PR_SET_NAME, STILL_HAVE_PRCTL="yes", STILL_HAVE_PRCTL="no", [#include <sys/prctl.h>])
dnl 	if test "x$STILL_HAVE_PRCTL" = "xyes"; then
dnl 		AC_DEFINE(HAVE_PRCTL, 1, [Defined as 1 if prctl and PR_SET_NAME are available])
dnl 	fi
dnl fi

dnl ****************************************************************************
dnl * Check for DBUS Services directory
dnl ****************************************************************************
DBUS_SERVICES_DIR="$DATADIR/dbus-1/services"
AC_SUBST(DBUS_SERVICES_DIR)
AC_DEFINE_UNQUOTED(DBUS_SERVICES_DIR, "$DBUS_SERVICES_DIR", [DBus services directory])

dnl ****************************************************************************
dnl * --------------------------------------------------------------------------
dnl ****************************************************************************
AC_OUTPUT([
Makefile
conduit/Makefile
conduit/defs.py
conduit/datatypes/Makefile
conduit/dataproviders/Makefile
conduit/evolution/Makefile
data/Makefile
data/conduit.desktop.in
data/conduit.pc
po/Makefile.in
])

echo
echo $PACKAGE v$VERSION
echo

echo Prefix............... : $prefix
echo Evolution Support.... : $enable_libebook
echo Dbus Services Dir.... : $DBUS_SERVICES_DIR

echo "Now type make to compile"
echo "Then su to root and type: make install"
echo
