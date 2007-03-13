SUBDIRS = \
	BackpackModule \
	FileModule \
	FeedModule \
	FlickrModule \
	FspotModule \
	GmailModule \
	SettingsModule

conduit_handlersdir = $(libdir)/conduit/dataproviders
conduit_handlers_PYTHON = \
	__init__.py \
	iPodModule.py \
	TomboyModule.py \
	ConverterModule.py

if ENABLE_EVOLUTION
	conduit_handlers_PYTHON += EvolutionModule.py
endif

clean-local:
	rm -rf *.pyc *.pyo
