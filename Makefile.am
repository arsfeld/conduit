SUBDIRS = conduit data

DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

EXTRA_DIST = \
	TODO \
	intltool-update.in \
	intltool-extract.in	\
	intltool-merge.in \
	doap.rdf doap.rdf.in

doap.rdf: doap.rdf.in Makefile.am
	sed -e s/\@VERSION\@/$(VERSION)/g \
	    -e s/\@MAJMIN\@/`echo $(VERSION) | sed "s|\([[:digit:]]\+\.[[:digit:]]\+\).*|\1|"`/g \
	    -e s/\@DATE\@/`date +%F`/g \
	< $< > $@

WEBROOT := root@www.greenbirdsystems.com:/var/www/conduit-project.org/files/releases
release: dist doap.rdf
	svn cp ../trunk/ ../tags/$(VERSION)	
	scp $(PACKAGE)-$(VERSION).tar.gz $(WEBROOT)
