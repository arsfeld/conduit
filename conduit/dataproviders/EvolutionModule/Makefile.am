if ENABLE_EVOLUTION
	conduit_handlersdir = $(libdir)/conduit/dataproviders/EvolutionModule
	conduit_handlers_PYTHON = EvolutionModule.py

	conduit_handlers_DATA = config.glade
endif

EXTRA_DIST = EvolutionModule.py config.glade

clean-local:
	rm -rf *.pyc *.pyo
