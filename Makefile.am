SUBDIRS = conduit data po help tools

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper --disable-nautilus-extension --disable-eog-plugin

release: dist
	svn cp ../trunk/ svn+ssh://jstowers@svn.gnome.org/svn/conduit/tags/$(VERSION) -m "Release $(VERSION)"	
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
	gnome-doc-utils.make


