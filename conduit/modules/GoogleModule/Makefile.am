SUBDIRS = gdata atom

conduit_handlersdir = $(libdir)/conduit/modules/GoogleModule
conduit_handlers_PYTHON = GoogleModule.py

conduit_handlers_DATA = \
	calendar-config.glade \
	picasa-config.glade \
	youtube-config.glade \
	contacts-config.glade \
	documents-config.glade

EXTRA_DIST = \
	calendar-config.glade \
	picasa-config.glade \
	youtube-config.glade \
	contacts-config.glade \
	documents-config.glade

clean-local:
	rm -rf *.pyc *.pyo
