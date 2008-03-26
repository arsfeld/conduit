"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""
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

