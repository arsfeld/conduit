INCLUDES = $(PYTHON_INCLUDES) $(EVOLUTION_CFLAGS)

_evolutiondir = $(pythondir)/conduit/evolution
_evolution_LTLIBRARIES = _evolution.la
_evolution_la_LDFLAGS = -module -avoid-version -export-symbols-regex init_evolution
_evolution_la_LIBADD = $(EVOLUTION_LIBS)
_evolution_la_SOURCES = \
	_evolutionmodule.c \
	override_common.c \
	evo-environment.c \
	evo-contact.c \
	evo-addressbook.c \
	override_common.h \
	evo-environment.h \
	evo-contact.h \
	evo-addressbook.h

nodist__evolution_la_SOURCES = _evolution.c

_evolution_PYTHON = \
	__init__.py

CLEANFILES = _evolution.c
EXTRA_DIST = \
	_evolution.defs \
	_evolution.override \
	gen-defs.sh

_evolution.c: _evolution.defs _evolution.override
.defs.c:
	(cd $(srcdir) \
	 && $(PYGTK_CODEGEN) \
	    --override $*.override \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c

