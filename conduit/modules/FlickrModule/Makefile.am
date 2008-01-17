SUBDIRS = flickrapi

conduit_handlersdir = $(libdir)/conduit/modules/FlickrModule
conduit_handlers_PYTHON = FlickrModule.py

conduit_handlers_DATA = config.glade
EXTRA_DIST = config.glade

clean-local:
	rm -rf *.pyc *.pyo
