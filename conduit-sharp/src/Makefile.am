ASSEMBLY_NAME = conduit-sharp
ASSEMBLY = $(ASSEMBLY_NAME).dll
SOURCES = \
	Application.cs		\
	Conduit.cs		\
	DataProvider.cs		\
	Delegates.cs		\
	Exporter.cs		\
	SyncSet.cs		\
	Util.cs

all: $(ASSEMBLY)

$(ASSEMBLY): $(SOURCES)
	$(MCS) -out:$@ -debug -target:library -nowarn:0169 -unsafe $(NDESKDBUS_LIBS) $(SOURCES) AssemblyInfo.cs

install-data-local:
	$(GACUTIL) /i $(ASSEMBLY) /f /package $(ASSEMBLY_NAME) /gacdir $(DESTDIR)$(libdir)

uninstall-local:
	$(GACUTIL) /u $(ASSEMBLY_NAME) /package $(ASSEMBLY_NAME) /gacdir $(libdir) /root $(DESTDIR)$(libdir)

CLEANFILES = $(ASSEMBLY) *.mdb
DISTCLEANFILES = Makefile.in
EXTRA_DIST = \
	$(SOURCES) \
	$(srcdir)/AssemblyInfo.cs.in \
	$(srcdir)/$(ASSEMBLY_NAME).snk


