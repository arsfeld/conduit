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
dnl * Write the values of various paths for start_conduit.py
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

AS_AC_EXPAND(BINDIR, $bindir)
AC_SUBST(BINDIR)
		
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
dnl * Check for neccessary python modules (that dont install pc files)
dnl ****************************************************************************
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

dnl ****************************************************************************
dnl * Check evolution-python to build the evolution dataprovider
dnl ****************************************************************************
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

dnl ****************************************************************************
dnl * Check sync-python to build the opensync dataprovider
dnl ****************************************************************************
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
conduit/datatypes/Makefile
conduit/dataproviders/Makefile
data/Makefile
data/conduit.desktop.in
data/conduit.pc
po/Makefile.in
])

echo
echo $PACKAGE v$VERSION
echo
echo Prefix............... : $prefix
echo Evolution Support.... : $have_evolution
echo Opensync Support..... : $have_opensync
echo Dbus Services Dir.... : $DBUS_SERVICES_DIR
echo
echo "Now type make to compile"
echo "Then su to root and type: make install"
echo
