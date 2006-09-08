PREFIX=/usr
CWD=`pwd`
PYTHON_VERSION=2.4
VERSION=0.2.0
#PYTHON_VERSION=`python -V 2>&1 | sed -e "s/Python //" | cut --bytes=1-3`
PYTHON_PATH=$(DESTDIR)$(PREFIX)/lib/python$(PYTHON_VERSION)/site-packages
all:
	@echo -e "Conduit does not require building\n"
	@echo "Type: 'make install' if you wish to install conduit to $(DESTDIR)$(PREFIX)"
	@echo "Set DESTDIR env var to change install location"

doc/index.html:
	./make-doc.sh
	
doc: doc/index.html
	
upload-doc: doc
	./upload-doc.sh

make-install-dirs: 
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	mkdir -p $(DESTDIR)$(PREFIX)/share/
	mkdir -p $(DESTDIR)$(PREFIX)/share/pixmaps
	mkdir -p $(DESTDIR)$(PREFIX)/share/applications
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit/data
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit/dataproviders
	mkdir -p $(PYTHON_PATH)/conduit
	mkdir -p $(PYTHON_PATH)/conduit/datatypes
	mkdir -p ~/.conduit
	mkdir -p ~/.conduit/modules

install: make-install-dirs
	install -m 644 conduit/data/*.png $(DESTDIR)$(PREFIX)/share/conduit/data
	install -m 644 conduit/data/conduit-icon.png $(DESTDIR)$(PREFIX)/share/pixmaps
	install -m 644 conduit/data/conduit.glade $(DESTDIR)$(PREFIX)/share/conduit/data
	install -m 644 conduit/dataproviders/*.py $(DESTDIR)$(PREFIX)/share/conduit/dataproviders
	install -m 644 conduit.desktop $(DESTDIR)$(PREFIX)/share/applications/
	install -m 644 conduit/*.py $(PYTHON_PATH)/conduit
	install -m 644 conduit/datatypes/*.py $(PYTHON_PATH)/conduit/datatypes
	install -m 755 conduit/start_conduit.py $(DESTDIR)$(PREFIX)/bin/conduit
	@#ln -sf $(CWD)/doc/ExampleModule.py ~/.conduit/modules/WikiModule.py

clean:
	find . -name "*.pyc" -exec rm {} \;
	find . -name "*.pyo" -exec rm {} \;
	find . -name "*.*~" -exec rm {} \;

tarball: clean
	tar --exclude .svn -czvf ../Conduit-$(VERSION).tar.gz conduit

release: tarball upload-doc doc
	@echo "Tagging Release"
    #svn cp conduit ../tags/$(VERSION)
	
uninstall:
	rm -r $(DESTDIR)$(PREFIX)/share/conduit
	rm -r $(DESTDIR)$(PREFIX)/share/applications/conduit.desktop
	rm -r $(PYTHON_PATH)/conduit
	rm -r $(DESTDIR)$(PREFIX)/bin/conduit
