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
#PKG_CHECK_MODULES(CONDUIT,
#	gtk+-2.0				>= 2.10
#	pygtk-2.0				>= 2.10
#	pygobject-2.0			>= 2.6
#)
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
EVOLUTION_PYTHON_REQUIRED=0.0.0
AC_ARG_ENABLE(evolution, AC_HELP_STRING([--disable-evolution],[Disable evolution support]),,[enable_evolution=yes])
if test "x$enable_evolution" = "xyes"; then
	PKG_CHECK_MODULES(EVOLUTION, [
		evolution-python >= $EVOLUTION_PYTHON_REQUIRED],
		[have_evolution=yes] , [have_evolution=no])
else
	have_evolution="no (disabled)"
fi
AM_CONDITIONAL(ENABLE_EVOLUTION, test "$have_evolution" = "yes")

################################################################################
# Check for sync-python to build the opensync dataprovider
################################################################################
SYNC_PYTHON_REQUIRED=0.0.0
AC_ARG_ENABLE(opensync, AC_HELP_STRING([--disable-opensync],[Disable opensync support]),,[enable_opensync=yes])
if test "x$enable_opensync" = "xyes"; then
	PKG_CHECK_MODULES(OPENSYNC, [
		sync-python >= $SYNC_PYTHON_REQUIRED],
		[have_opensync=yes] , [have_opensync=no])
else
	have_opensync="no (disabled)"
fi
AM_CONDITIONAL(ENABLE_OPENSYNC, test "$have_opensync" = "yes")

################################################################################
# DBus
################################################################################
DBUS_REQUIRED=0.93
AC_ARG_ENABLE(dbus, AC_HELP_STRING([--disable-dbus],[Disable dbus service]),,[enable_dbus=yes])
if test "x$enable_dbus" = "xyes"; then
	PKG_CHECK_MODULES(DBUS, [
		dbus-1 >= $DBUS_REQUIRED],
		[have_dbus=yes] , [have_dbus=no])
	DBUS_SERVICES_DIR=`$PKG_CONFIG --variable=session_bus_services_dir dbus-1`
	AC_SUBST(DBUS_SERVICES_DIR)
else
	have_dbus="no (disabled)"
fi
AM_CONDITIONAL(ENABLE_DBUS, test "$have_dbus" = "yes")


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
conduit/dataproviders/FileModule/Makefile
conduit/dataproviders/FeedModule/Makefile
conduit/dataproviders/FlickrModule/Makefile
conduit/dataproviders/FlickrModule/FlickrAPI-8/Makefile
conduit/dataproviders/FspotModule/Makefile
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
echo Opensync Support..... : $have_opensync
echo Dbus Service......... : $have_dbus
echo Dbus Services Dir.... : $DBUS_SERVICES_DIR
echo
