"""
Interfaces for inter-operation with opensync

Copyright: John Stowers, 2006
License: GPLv2
"""

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.Module as Module
import conduit.Utils as Utils
from conduit.datatypes import DataType

from conduit.DataProvider import DataSource
from conduit.DataProvider import DataSink
from conduit.DataProvider import TwoWay

import opensync

MODULES = {
        "OpenSyncFactory" :        { "type": "dataprovider-factory" },
}

evo_config = """<config>
                    <address_path>default</address_path>
                    <calendar_path>default</calendar_path>
                    <tasks_path>default</tasks_path>
                </config>"""

class OpenSyncFactory(DataProvider.DataProviderFactory):
    def __init__(self, *args, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, *args, **kwargs)

        # Create a Format Environment and load plugins in to it
        self.formats = opensync.FormatEnv()
        self.formats.load_plugins()

        # Create a Plugins Environment and load plugins in to it
        self.plugins = opensync.PluginEnv()
        self.plugins.load()

    def probe(self):
        for plugin in self.plugins.plugins:
            self.plugin_available(plugin)

    def plugin_available(self, plugin):
        category = DataProvider.DataProviderCategory(plugin.name)

        info = opensync.PluginInfo()
        info.set_config(evo_config)
        info.set_format_env(self.formats)

        d = plugin.initialize(info)
        plugin.discover(d, info)

        for sink in info.objtypes:
            info.sink = sink
            self.sink_available(plugin, sink, d, info, category)

    def sink_available(self, plugin, sink, data, info, category):
        fields = { 
            "_name_":         sink.name,
            "_description_":  plugin.description,
            "_module_type_":  "twoway",
            "_in_type_":      "file",
            "_out_type_":     "file",
            "_icon_":         "contact-new",
            "sink":           sink,
            "data":           data,
            "info":           info,
        }
        name = "opensync-" + plugin.name + "-" + sink.name
        dataprovider = type(name, (OpenSyncDataprovider, ), fields)

        key = self.emit_added(
                                  dataprovider, 
                                  (name, ), 
                                  category
                             )

class OpenSyncDataprovider(DataProvider.TwoWay):
    """
    Generic dataprovider for interfacing with OpenSync plugins
    """

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.ctx = opensync.Context()
        self.ctx.set_callback_object(Callbacks())

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.sink.connect(self.data, self.info, self.ctx)
        logd(">>> Connected to opensync dataprovider")
        self.sink.get_changes(self.data, self.info, self.ctx)
        logd(">>> Changes were got :D")

    def get_all(self):
        return []

    def get(self, LUID):
        return None

    def put(self, obj, overwrite, LUID=None):
        return ""

    def delete(self, LUID):
        return

    def finish(self):
        self.sink.disconnect(self.data, self.info, self.ctx)

    def get_UID(self):
        return "foobar"

class Callbacks(opensync.ContextCallbacks):
    def callback(self, err):
        pass

    def changes(self, change):
        uid = change.uid
        data = change.data.data
#        hash = change.data.hash
        logd("change: %s, %s\n%s" % (uid,hash,data))

    def warning(self, err):
        logd("warning: %s" % err)

