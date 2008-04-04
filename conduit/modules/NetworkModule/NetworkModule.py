"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""
import sys
import logging
log = logging.getLogger("modules.Network")

#We need Python2.5 for network sync. This is because allow_none (i.e.
#the marshalling of None in the xmlrpc server) was only added in Python2.5
if sys.version_info[0:2] >= (2,5):
    import conduit.utils as Utils
    Utils.dataprovider_add_dir_to_path(__file__, "")

    import Client
    import Server

    NetworkClientFactory = Client.NetworkClientFactory
    NetworkServerFactory = Server.NetworkServerFactory
    NetworkEndpoint = Server.NetworkEndpoint

    MODULES = {
            "NetworkServerFactory" :     { "type": "dataprovider-factory" },
            "NetworkClientFactory" :     { "type": "dataprovider-factory" },
            "NetworkEndpoint"      :     { "type": "dataprovider" },
    }
    log.info("Network support enabled")
else:
    MODULES = {}
    log.info("Network support disabled")

