SUBDIRS = shutterfly

conduit_handlersdir = $(libdir)/conduit/modules/ShutterflyModule
conduit_handlers_PYTHON = ShutterflyModule.py

conduit_handlers_DATA = shutterfly.glade
EXTRA_DIST = shutterfly.glade

clean-local:
	rm -rf *.pyc *.pyo
