SAMPLES=test-application.cs 
MCSFLAGS= -debug -nologo -r:conduit-sharp.dll

EXTRA_DIST=$(SAMPLES)
CLEANFILES= *.exe *.mdb *.pdb *.dll

noinst_SCRIPTS=$(SAMPLES:.cs=.exe)

%.exe: %.cs conduit-sharp.dll
	$(MCS) $(MCSFLAGS) `pkg-config --libs glib-sharp-2.0` -out:$@ $<

conduit-sharp.dll: $(top_builddir)/src/conduit-sharp.dll
	cp $(top_builddir)/src/conduit-sharp.dll* .

