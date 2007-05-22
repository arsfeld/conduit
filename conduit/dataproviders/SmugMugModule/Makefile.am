SUBDIRS = SmugMugAPI

conduit_handlersdir = $(libdir)/conduit/dataproviders/SmugMugModule
conduit_handlers_PYTHON = SmugMugModule.py

conduit_handlers_DATA = config.glade
EXTRA_DIST = config.glade

clean-local:
	rm -rf *.pyc *.pyo
