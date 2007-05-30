SUBDIRS = \
	BackpackModule \
	FileModule \
	FeedModule \
	FlickrModule \
	FspotModule \
	GmailModule \
	PicasaModule \
	SettingsModule \
	SmugMugModule

conduit_handlersdir = $(libdir)/conduit/dataproviders
conduit_handlers_PYTHON = \
	__init__.py \
	iPodModule.py \
	TomboyModule.py \
	ConverterModule.py

if ENABLE_EVOLUTION
	SUBDIRS += EvolutionModule
endif

clean-local:
	rm -rf *.pyc *.pyo
