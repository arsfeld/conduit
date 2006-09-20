#Conduit Version Number
VERSION=`cat conduit/__init__.py | grep 'APPVERSION=\"' | sed -e 's/APPVERSION=//' -e 's/\"//g'`

#Install prefix, can be overridden by setting DESTDIR
PREFIX=/usr
CWD=`pwd`

#Python version for installation into python dir
PYTHON_VERSION=2.4
#PYTHON_VERSION=`python -V 2>&1 | sed -e "s/Python //" | cut --bytes=1-3`
PYTHON_PATH=$(DESTDIR)$(PREFIX)/lib/python$(PYTHON_VERSION)/site-packages

#Source Files
SRC=conduit/*.py conduit/dataproviders/*.py conduit/datatypes/*.py

all:
	@echo -e "Conduit v$(VERSION) does not require building\n"
	@echo "Type: 'make install' if you wish to install conduit to $(DESTDIR)$(PREFIX)"
	@echo "Set DESTDIR env var to change install location"
	

doc-stamp: $(SRC)
	@echo "Making Docs"
	@touch doc-stamp
	@./scripts/make-doc.sh
	
doc: doc-stamp
	
upload-doc: doc
	@./scripts/upload-doc.sh

make-install-dirs: 
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	mkdir -p $(DESTDIR)$(PREFIX)/share/
	mkdir -p $(DESTDIR)$(PREFIX)/share/pixmaps
	mkdir -p $(DESTDIR)$(PREFIX)/share/applications
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit/contrib
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit/data
	mkdir -p $(DESTDIR)$(PREFIX)/share/conduit/dataproviders
	mkdir -p $(PYTHON_PATH)/conduit
	mkdir -p $(PYTHON_PATH)/conduit/datatypes
	mkdir -p ~/.conduit
	mkdir -p ~/.conduit/modules
	@for i in `ls contrib`; do \
		( mkdir -p $(DESTDIR)$(PREFIX)/share/conduit/contrib/$$i ) \
	done


install: make-install-dirs
	install -m 644 conduit/data/*.png $(DESTDIR)$(PREFIX)/share/conduit/data
	install -m 644 conduit/data/conduit-icon.png $(DESTDIR)$(PREFIX)/share/pixmaps
	install -m 644 conduit/data/conduit.glade $(DESTDIR)$(PREFIX)/share/conduit/data
	install -m 644 conduit/dataproviders/*.py $(DESTDIR)$(PREFIX)/share/conduit/dataproviders
	install -m 644 conduit.desktop $(DESTDIR)$(PREFIX)/share/applications/
	install -m 644 conduit/*.py $(PYTHON_PATH)/conduit
	install -m 644 conduit/datatypes/*.py $(PYTHON_PATH)/conduit/datatypes
	install -m 755 conduit/start_conduit.py $(DESTDIR)$(PREFIX)/bin/conduit
	@for i in `ls contrib`; do \
		( install -m 644 contrib/$$i/*.py $(DESTDIR)$(PREFIX)/share/conduit/contrib/$$i ) \
	done
	ln -sf $(CWD)/doc/ExampleModule.py ~/.conduit/modules/MoinModule.py

clean: clean-bin
	-rm dist-stamp
	-rm doc-stamp	
	
clean-bin:
	@echo "Cleaning..."
	find . -name "*.pyc" -exec rm {} \;
	find . -name "*.pyo" -exec rm {} \;
	find . -name "*.*~" -exec rm {} \;

tarball: clean-bin $(SRC) dist-files
	@echo "Creating Tarball"
	tar --exclude .svn -czf ../conduit-$(VERSION).tar.gz \
	    conduit contrib Makefile TODO NEWS README AUTHORS MAINTAINERS

dist-stamp:
	@touch dist-stamp
	@echo "Updating ChangeLog"
	@-svn2cl.sh --output=conduit/ChangeLog
	@echo "Updating TODO"
	@-wget -q -O - http://www.conduit-project.org/wiki/TODO?format=txt > TODO
	@echo "Updating NEWS"
	@-wget -q -O - http://www.conduit-project.org/wiki/Status?format=txt > NEWS
	
dist-files: dist-stamp

deb: $(SRC)
	@echo "Building Deb File"
	@./scripts/make-deb.sh $(VERSION)
	debuild clean

release: tarball upload-doc deb
	@echo "Tagging Release"
	svn cp ../trunk/ ../tags/$(VERSION)
	
uninstall:
	rm -r $(DESTDIR)$(PREFIX)/share/conduit
	rm -r $(DESTDIR)$(PREFIX)/share/applications/conduit.desktop
	rm -r $(PYTHON_PATH)/conduit
	rm -r $(DESTDIR)$(PREFIX)/bin/conduit
	rm ~/.conduit/modules/MoinModule.py
