SUBDIRS = datatypes dataproviders

start_conduit: start_conduit.py
	sed -e "s|\@PYTHONDIR\@|$(pythondir)|" \
		-e "s|\@VERSION\@|$(VERSION)|" \
		-e "s|\@LOCALEDIR\@|$(LOCALEDIR)|" \
		-e "s|\@PKGDATADIR\@|$(PKGDATADIR)|" \
		-e "s|\@PKGLIBDIR\@|$(PKGLIBDIR)|" \
	$< > $@

conduitbindir = $(bindir)
conduitbin_SCRIPTS = start_conduit

conduitdir = $(pythondir)/conduit
conduit_PYTHON = \
	__init__.py \
	Canvas.py \
	Conduit.py \
	Conflict.py \
	DataProvider.py \
	DB.py \
	DBus.py \
	DeltaProvider.py \
	Exceptions.py \
	Hal.py \
	MainWindow.py \
	Module.py \
	ModuleWrapper.py \
	Settings.py \
	Synchronization.py \
	Tree.py \
	TypeConverter.py \
	Utils.py \
	VolumeMonitor.py

	
BUILT_SOURCES = \
	start_conduit
	
CLEANFILES = \
	$(BUILT_SOURCES)
	
DISTCLEANFILES = \
	$(CLEANFILES)
	
EXTRA_DIST = \
	start_conduit.py

clean-local:
	rm -rf *.pyc *.pyo
