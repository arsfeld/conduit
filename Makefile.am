SUBDIRS = conduit data po help tools

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper --disable-nautilus-extension --disable-eog-plugin

doap.rdf: doap.rdf.in Makefile.am
	sed -e s/\@VERSION\@/$(VERSION)/g \
	    -e s/\@MAJMIN\@/`echo $(VERSION) | sed "s|\([[:digit:]]\+\.[[:digit:]]\+\).*|\1|"`/g \
	    -e s/\@DATE\@/`date +%F`/g \
	< $< > $@

release: dist doap.rdf
	svn cp ../trunk/ ../tags/$(VERSION)	
	scp $(PACKAGE)-$(VERSION).tar.gz jstowers@master.gnome.org:
	ssh jstowers@master.gnome.org install-module $(PACKAGE)-$(VERSION).tar.gz

DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update \
	gnome-doc-utils.make

EXTRA_DIST = \
	NEWS \
	TODO \
	ChangeLog \
	intltool-update.in \
	intltool-extract.in	\
	intltool-merge.in \
	doap.rdf \
	doap.rdf.in \
	gnome-doc-utils.make


