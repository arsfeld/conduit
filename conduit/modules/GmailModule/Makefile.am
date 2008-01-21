SUBDIRS = libgmail

conduit_handlersdir = $(libdir)/conduit/modules/GmailModule
conduit_handlers_PYTHON = GmailModule.py

conduit_handlers_DATA = config.glade
EXTRA_DIST = config.glade

clean-local:
	rm -rf *.pyc *.pyo
