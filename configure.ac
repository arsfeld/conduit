AC_INIT([conduit], [0.3.3],[john.stowers@gmail.com],[conduit])
AM_INIT_AUTOMAKE([1.9])
AC_CONFIG_SRCDIR(conduit/__init__.py)
AC_CONFIG_MACRO_DIR([m4])
AM_MAINTAINER_MODE
AC_SUBST(ACLOCAL_AMFLAGS, "$ACLOCAL_FLAGS -I m4")

################################################################################
# Translation & i18n
################################################################################
GETTEXT_PACKAGE="conduit"
AC_SUBST([GETTEXT_PACKAGE])
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
IT_PROG_INTLTOOL([0.35.0])

################################################################################
# Gnome Doc Utils
################################################################################
GNOME_DOC_INIT

################################################################################
# Requirements
################################################################################
AM_PATH_PYTHON(2.4)

AC_CHECK_PROG(HAVE_PKGCONFIG, pkg-config, yes, no)
if test "x$HAVE_PKGCONFIG" = "xno"; then
  AC_MSG_ERROR(you need to have pkgconfig installed !)
fi

################################################################################
# Check for neccessary python modules (that dont install pc files)
################################################################################
AM_CHECK_PYMOD([vobject], , , AC_MSG_ERROR([Python module vobject required to run Conduit]))

AM_CHECK_PYMOD([goocanvas], , , AC_MSG_ERROR([Python module goocanvas >= 0.8.0 required to run Conduit]))

AM_CHECK_PYMOD([dateutil], , , AC_MSG_ERROR([Python module dateutil required to run Conduit]))

################################################################################
# DBus
################################################################################
PKG_CHECK_MODULES(DBUS, [ dbus-1 >= 0.93 ])

AC_ARG_WITH([session_bus_services_dir],
            AC_HELP_STRING([--with-session-bus-services-dir], [Path to DBus services directory]))

if test "x$with_dbus_service_dir" != "x"; then
	DBUS_SERVICES_DIR=$with_dbus_service_dir
else
	DBUS_SERVICES_DIR=${datadir}/dbus-1/services
fi
AC_SUBST(DBUS_SERVICES_DIR)

################################################################################
# Write the values of various paths for start_conduit.py
################################################################################
AC_SUBST(VERSION)
AC_SUBST(PACKAGE)

AS_AC_EXPAND(LOCALEDIR, $localedir)
AS_AC_EXPAND(PKGDATADIR, $datarootdir/$PACKAGE)
AS_AC_EXPAND(ICONDIR, $datarootdir/$PACKAGE/icons)
AS_AC_EXPAND(LIBDIR, $libdir)
AS_AC_EXPAND(PKGLIBDIR, $libdir/$PACKAGE)
AS_AC_EXPAND(PYTHONDIR, $pythondir)
AS_AC_EXPAND(BINDIR, $bindir)

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
conduit/dataproviders/BoxDotNetModule/Makefile
conduit/dataproviders/BoxDotNetModule/BoxDotNetAPI/Makefile
conduit/dataproviders/EvolutionModule/Makefile
conduit/dataproviders/FileModule/Makefile
conduit/dataproviders/FeedModule/Makefile
conduit/dataproviders/FlickrModule/Makefile
conduit/dataproviders/FlickrModule/FlickrAPI/Makefile
conduit/dataproviders/FspotModule/Makefile
conduit/dataproviders/GmailModule/Makefile
conduit/dataproviders/GmailModule/libgmail-0.1.5/Makefile
conduit/dataproviders/PicasaModule/Makefile
conduit/dataproviders/PicasaModule/PicasaAPI/Makefile
conduit/dataproviders/SettingsModule/Makefile
conduit/dataproviders/SettingsModule/settings/Makefile
conduit/dataproviders/SmugMugModule/Makefile
conduit/dataproviders/SmugMugModule/SmugMugAPI/Makefile
data/Makefile
data/conduit.desktop.in
data/conduit-autostart.desktop.in
data/conduit.pc
data/icons/Makefile
data/icons/16x16/Makefile
data/icons/16x16/actions/Makefile
data/icons/16x16/apps/Makefile
data/icons/16x16/status/Makefile
data/icons/22x22/Makefile
data/icons/22x22/apps/Makefile
data/icons/32x32/Makefile
data/icons/32x32/apps/Makefile
data/icons/48x48/apps/Makefile
data/icons/48x48/Makefile
data/icons/scalable/Makefile
data/icons/scalable/apps/Makefile
po/Makefile.in
help/Makefile
)

echo
echo $PACKAGE v$VERSION
echo
echo Prefix............... : $prefix
echo Dbus Services Dir.... : $DBUS_SERVICES_DIR
echo

