AC_INIT(libevo, 0.0.1, john.stowers@gmail.com)
AC_PREREQ(2.50)
AC_COPYRIGHT([Copyright 2006 John Stowers])
PACKAGE=libevo
VERSION=0.0.1

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)
AM_CONFIG_HEADER(config.h)

AC_PROG_CC
AC_PROG_CPP
AC_PROG_MAKE_SET
AC_PROG_LN_S
AC_PROG_INSTALL
AC_C_CONST
AC_EXEEXT
AM_PROG_LIBTOOL

PKG_CHECK_MODULES(PACKAGE, [evolution-data-server-1.2 libedataserver-1.2 libebook-1.2 libecal-1.2 gdk-pixbuf-2.0 pango])
AC_SUBST(PACKAGE_CFLAGS)
AC_SUBST(PACKAGE_LIBS)

if test "x$GCC" = "xyes"; then
	CFLAGS="$CFLAGS -Wall"
fi

AC_SUBST(CFLAGS)

AC_CONFIG_FILES([
libevo.pc
Makefile
src/Makefile
tests/Makefile
])

AC_OUTPUT

echo
echo $PACKAGE $VERSION

echo
echo "Now type make to compile"
echo "Then sudo to root and type: make install"
echo
