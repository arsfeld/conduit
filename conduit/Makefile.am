SUBDIRS = datatypes dataproviders

if ENABLE_EVOLUTION
SUBDIRS += evolution
endif
	
#start_conduit: start_conduit.py
#	sed -e "s|\@PYTHONDIR\@|$(pythondir)/conduit|" $< > $@
#conduitbindir = $(libdir)/conduit

conduitbindir = $(bindir)
conduitbin_SCRIPTS = start_conduit.py

conduitdir = $(pythondir)/conduit
conduit_PYTHON = \
	defs.py \
	__init__.py \
	Canvas.py \
	Conduit.py \
	Conflict.py \
	DataProvider.py \
	DBus.py \
	DeltaProvider.py \
	Exceptions.py \
	Hal.py \
	MainWindow.py \
	Module.py \
	ModuleWrapper.py \
	Network.py \
	Settings.py \
	Synchronization.py \
	Tree.py \
	TreeViewTooltips.py \
	TypeConverter.py \
	Utils.py \
	VolumeMonitor.py

	
#BUILT_SOURCES = \
#	start_conduit
	
#CLEANFILES = \
#	$(BUILT_SOURCES)
	
DISTCLEANFILES = \
	defs.py 
#	$(CLEANFILES)
	
EXTRA_DIST = \
	defs.py.in \
	start_conduit.py
