SUBDIRS = datatypes dataproviders modules gtkui hildonui utils platform

conduitbindir = $(bindir)
conduitbin_SCRIPTS = \
	conduit.real \
	conduit

conduitdir = $(pythondir)/conduit
conduit_PYTHON = \
	Conduit.py \
	Conflict.py \
	Database.py \
	DBus.py \
	defs.py \
	DeltaProvider.py \
	Exceptions.py \
	Globals.py \
	__init__.py \
	Knowledge.py \
	Logging.py \
	Main.py \
	MappingDB.py \
	Module.py \
	ModuleWrapper.py \
	Settings.py \
	Synchronization.py \
	SyncSet.py \
	TypeConverter.py \
	Vfs.py \
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
