"""
Contains classes for advertising conduit via avahi and for transmitting and
receiving python objects over the network.

Copyright: John Stowers, 2006
License: GPLv2
"""

import conduit
import conduit.Utils as Utils

Utils.dataprovider_add_dir_to_path(__file__, "")
import Server
import Client

#import NetworkModule.Client as Client
#import NetworkModule.Server as Server

NetworkClientFactory = Client.NetworkClientFactory
NetworkServerFactory = Server.NetworkServerFactory

MODULES = {
        "NetworkServerFactory" :     { "type": "dataprovider-factory" },
        "NetworkClientFactory" :     { "type": "dataprovider-factory" },
}

