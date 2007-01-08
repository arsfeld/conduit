SUBDIRS = \
	BackpackModule \
	FileModule \
	FeedModule \
	FlickrModule \
	FspotModule \
	GmailModule

conduit_handlersdir = $(libdir)/conduit/dataproviders
conduit_handlers_PYTHON = \
	ContactConverterModule.py \
	__init__.py \
	iPodModule.py \
	NotesModule.py \
	SynceModule.py \
	TextConverterModule.py

if ENABLE_EVOLUTION
	conduit_handlers_PYTHON += EvolutionModule.py
endif

clean-local:
	rm -rf *.pyc *.pyo
