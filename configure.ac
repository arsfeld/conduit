AC_PREREQ(2.57)
AC_INIT([conduit], [0.3.0],[mailto:john.stowers@gmail.com],[conduit])
AM_INIT_AUTOMAKE([1.9])

AC_CONFIG_SRCDIR(conduit/__init__.py)
AC_CONFIG_HEADERS(config.h)
AC_CONFIG_MACRO_DIR([m4])

AM_MAINTAINER_MODE

AC_PROG_CC
AC_ISC_POSIX
AC_HEADER_STDC
AC_PROG_LIBTOOL

################################################################################
# GNOME
################################################################################
GNOME_COMMON_INIT

################################################################################
# Python 2.4
################################################################################
AM_PATH_PYTHON(2.4)

################################################################################
# Translation & i18n
################################################################################
GETTEXT_PACKAGE="conduit"
IT_PROG_INTLTOOL([0.35.0])
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])
AM_GLIB_GNU_GETTEXT

################################################################################
# GConf support
################################################################################
#AC_PATH_PROG(GCONFTOOL, gconftool-2)
#AM_GCONF_SOURCE_2

################################################################################
# Requirements
################################################################################
#Dont actually need any devel modules at the moment - bindings are out of tree
PKG_CHECK_MODULES(CONDUIT,
	gtk+-2.0				>= 2.10
	pygtk-2.0				>= 2.10
)
#AC_SUBST(CONDUIT_CFLAGS)
#AC_SUBST(CONDUIT_LIBS)

################################################################################
# Check for neccessary python modules (that dont install pc files)
################################################################################
AC_MSG_CHECKING([for vobject module])
if AC_RUN_LOG([$PYTHON -c '
try:
    import vobject
except ImportError, e:
    if str(e).find("vobject") >= 0:
          raise
except:
    pass
']); then
  AC_MSG_RESULT([yes])
else
  AC_MSG_RESULT([no])
  AC_MSG_ERROR([Python module vobject required to run conduit])
fi

################################################################################
# Check for evolution-python to build the evolution dataprovider
################################################################################
AC_ARG_ENABLE([evolution],
              AC_HELP_STRING([--enable-evolution], [Enable support for evolution]),,
              [enable_evolution=no])

if test "x$enable_evolution" = "xyes"; then
	PKG_CHECK_MODULES(EVOLUTION, [evolution-python >= 0.0.0] ,
		[have_evolution=yes] , [have_evolution=no])
else
	have_evolution="no (disabled)"
fi
AM_CONDITIONAL(ENABLE_EVOLUTION, test "$have_evolution" = "yes")


################################################################################
# DBus
################################################################################
PKG_CHECK_MODULES(DBUS, [ dbus-1 >= 0.93 ])

AC_ARG_WITH([session_bus_services_dir],
            AC_HELP_STRING([--with-session-bus-services-dir], [Path to DBus services directory]))

if test "x$with_session_bus_services_dir" = "x" ; then
   services_dir="`pkg-config --variable session_bus_services_dir dbus-1`"
else
   services_dir="$with_session_bus_services_dir"
fi

DBUS_SERVICES_DIR="$services_dir"
AC_SUBST(DBUS_SERVICES_DIR)

################################################################################
# Write the values of various paths for start_conduit.py
################################################################################
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

AS_AC_EXPAND(BINDIR, $bindir)
AC_SUBST(BINDIR)

################################################################################
#-------------------------------------------------------------------------------
################################################################################
AC_OUTPUT(
Makefile
conduit/Makefile
conduit/datatypes/Makefile
conduit/dataproviders/Makefile
conduit/dataproviders/BackpackModule/Makefile
conduit/dataproviders/BackpackModule/backpack-1.1/Makefile
conduit/dataproviders/FileModule/Makefile
conduit/dataproviders/FeedModule/Makefile
conduit/dataproviders/FlickrModule/Makefile
conduit/dataproviders/FlickrModule/FlickrAPI/Makefile
conduit/dataproviders/FspotModule/Makefile
conduit/dataproviders/GmailModule/Makefile
conduit/dataproviders/GmailModule/libgmail-0.1.5/Makefile
conduit/dataproviders/SettingsModule/Makefile
conduit/dataproviders/SettingsModule/settings/Makefile
data/Makefile
data/conduit.desktop.in
data/conduit.pc
po/Makefile.in
)

echo
echo $PACKAGE v$VERSION
echo
echo Prefix............... : $prefix
echo Evolution Support.... : $have_evolution
echo Dbus Services Dir.... : $DBUS_SERVICES_DIR
echo
