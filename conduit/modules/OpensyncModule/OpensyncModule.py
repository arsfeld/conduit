import logging
log = logging.getLogger("modules.OpenSync")

import conduit
import conduit.Utils as Utils

Utils.dataprovider_add_dir_to_path(__file__, "")

MODULES = {}
SUPPORTED = False

try:
    import opensync
    SUPPORTED = True
except ImportError:
    log.warn("Skipping OpenSync support. Please install OpenSync bindings!")


if SUPPORTED == True:
    import SynceAdaptor
    MODULES.update(SynceAdaptor.MODULES)
    OS_SynceFactory = SynceAdaptor.OS_SynceFactory
    
    import EvolutionAdaptor
    MODULES.update(EvolutionAdaptor.MODULES)
    OS_Evolution_Contact = EvolutionAdaptor.OS_Evolution_Contact
    OS_Evolution_Event = EvolutionAdaptor.OS_Evolution_Event
