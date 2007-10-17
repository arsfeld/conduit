SUBDIRS = datatypes dataproviders modules

conduitbindir = $(bindir)
conduitbin_SCRIPTS = \
	conduit.real \
	conduit

conduitdir = $(pythondir)/conduit
conduit_PYTHON = \
	__init__.py \
	Canvas.py \
	Conduit.py \
	Conflict.py \
	DB.py \
	DBus.py \
	defs.py \
	DeltaProvider.py \
	Exceptions.py \
	Hal.py \
	Globals.py \
	GtkUI.py \
	Main.py \
	MappingDB.py \
	Module.py \
	ModuleWrapper.py \
	Settings.py \
	Synchronization.py \
	SyncSet.py \
	Tree.py \
	TypeConverter.py \
	Utils.py \
	Web.py
	
CLEANFILES = \
	defs.py \
	$(BUILT_SOURCES)
	
DISTCLEANFILES = \
	$(CLEANFILES)
	
EXTRA_DIST = \
	defs.py.in \
	conduit.real \
	conduit

clean-local:
	rm -rf *.pyc *.pyo
