SUBDIRS = settings

conduit_handlersdir = $(libdir)/conduit/dataproviders/SettingsModule
conduit_handlers_PYTHON = \
	SettingsModule.py \
	GConfUtils.py
conduit_handlers_DATA = config.glade

clean-local:
	rm -rf *.pyc *.pyo
