SUBDIRS = conduit data

DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

EXTRA_DIST = \
	NEWS \
	TODO \
	ChangeLog \
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

#Update ChangeLog, NEWS and TODO from http://www.conduit-project.org
dist-hook:
	./scripts/svn2cl.sh --output=ChangeLog.new
	mv -f ChangeLog.new $(distdir)/ChangeLog
	wget -q -O \
		- "http://www.conduit-project.org/query?status=closed&format=csv&milestone=$(VERSION)&order=priority" | \
		sed 1d | \
		awk -F , '{print $$2}' \
		> NEWS.new
	mv -f NEWS.new $(distdir)/NEWS
	wget -q -O TODO.new \
		"http://www.conduit-project.org/wiki/TODO?format=txt"
	mv -f TODO.new $(distdir)/TODO
