SUBDIRS = conduit data po help tools

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper --disable-nautilus-extension --disable-eog-plugin

doap.rdf: doap.rdf.in Makefile.am
	sed -e s/\@VERSION\@/$(VERSION)/g \
	    -e s/\@MAJMIN\@/`echo $(VERSION) | sed "s|\([[:digit:]]\+\.[[:digit:]]\+\).*|\1|"`/g \
	    -e s/\@DATE\@/`date +%F`/g \
	< $< > $@

WEBROOT := root@www.greenbirdsystems.com:/var/www/conduit-project.org/files/releases
release: dist doap.rdf
	svn cp ../trunk/ ../tags/$(VERSION)	
	scp $(PACKAGE)-$(VERSION).tar.gz $(WEBROOT)

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

#Update ChangeLog, NEWS and TODO from http://www.conduit-project.org
#Ugly autofoo to support make distcheck pass
dist-hook:
	@echo "Generating Changelog, NEWS, TODO"
	@if test -d $(top_srcdir)/.svn ; then \
		wget -q -O $(distdir)/NEWS "http://www.conduit-project.org/wiki/$(VERSION)?format=txt" ; \
		wget -q -O $(distdir)/TODO "http://www.conduit-project.org/wiki/TODO?format=txt" ; \
	else \
		touch $(distdir)/NEWS; \
		touch $(distdir)/TODO; \
	fi


