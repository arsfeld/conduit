SAMPLES=test-application.cs test-conduit.cs
MCSFLAGS= -debug -nologo -r:conduit-sharp.dll

EXTRA_DIST=$(SAMPLES)
CLEANFILES= *.exe *.mdb *.pdb *.dll

noinst_SCRIPTS=$(SAMPLES:.cs=.exe)

%.exe: %.cs conduit-sharp.dll
	$(MCS) $(MCSFLAGS) $(GTKSHARP_LIBS) $(NDESKDBUSGLIB_LIBS) -out:$@ $<

conduit-sharp.dll: $(top_builddir)/src/conduit-sharp.dll
	cp $(top_builddir)/src/conduit-sharp.dll* .

