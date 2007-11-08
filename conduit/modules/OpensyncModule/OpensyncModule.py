import conduit
from conduit import logw

MODULES = {}
SUPPORTED = False

try:
    import opensync
    SUPPORTED = True
except ImportError:
    logw("Skipping OpenSync support. Please install OpenSync bindings!")

if SUPPORTED:
    import SynceAdaptor
    MODULES.update(SynceAdaptor.MODULES)

    import EvolutionAdaptor
    MODULES.update(EvolutionAdaptor.MODULES)
