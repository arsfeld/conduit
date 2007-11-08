import conduit
import conduit.Utils as Utils
from conduit import logw

Utils.dataprovider_add_dir_to_path(__file__, "")

MODULES = {}
SUPPORTED = False

try:
    import opensync
    SUPPORTED = True
except ImportError:
    logw("Skipping OpenSync support. Please install OpenSync bindings!")

if SUPPORTED == True:
    import SynceAdaptor
    MODULES.update(SynceAdaptor.MODULES)

    import EvolutionAdaptor
    MODULES.update(EvolutionAdaptor.MODULES)
