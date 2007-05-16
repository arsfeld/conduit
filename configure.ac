AC_INIT([conduit], [0.3.1],[mailto:john.stowers@gmail.com],[conduit])
AM_INIT_AUTOMAKE([1.9])
AC_CONFIG_SRCDIR(conduit/__init__.py)
AM_MAINTAINER_MODE

################################################################################
# Translation & i18n
################################################################################
GETTEXT_PACKAGE="conduit"
AC_SUBST([GETTEXT_PACKAGE])
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
IT_PROG_INTLTOOL([0.35.0])

################################################################################
# Requirements
################################################################################
AM_PATH_PYTHON(2.4)

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

AC_MSG_CHECKING([for goocanvas module])
if AC_RUN_LOG([$PYTHON -c '
try:
    import goocanvas
except ImportError, e:
    if str(e).find("goocanvas") >= 0:
          raise
except:
    pass
']); then
  AC_MSG_RESULT([yes])
else
  AC_MSG_RESULT([no])
  AC_MSG_ERROR([Python module goocanvas required to run conduit])
fi

AC_MSG_CHECKING([for dateutil module])
if AC_RUN_LOG([$PYTHON -c '
try:
    import dateutil
except ImportError, e:
    if str(e).find("dateutil") >= 0:
          raise
except:
    pass
']); then
  AC_MSG_RESULT([yes])
else
  AC_MSG_RESULT([no])
  AC_MSG_ERROR([Python module dateutil required to run conduit])
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
conduit/dataproviders/SmugMugModule/Makefile
conduit/dataproviders/SmugMugModule/SmugMugAPI/Makefile
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
