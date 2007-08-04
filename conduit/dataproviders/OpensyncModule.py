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

import conduit.datatypes.Contact as Contact

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
        self.ctx.set_callback_object(Callbacks(self))
        self.uids = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.sink.connect(self.data, self.info, self.ctx)
        self.uids = {}
        self.sink.get_changes(self.data, self.info, self.ctx)

    def get_all(self):
        return list(self.uids.iterkeys())

    def get(self, LUID):
        return self.uids[LUID]

    def put(self, obj, overwrite, LUID=None):
        chg = opensync.Change()
        if overwrite == True:
            chg.uid = LUID
            chg.changetype = opensync.CHANGE_MODIFIED
        else:
            chg.changetype = opensync.CHANGE_ADDED

        # change.format = "plain"
        # change.objtype = "data"
        # change.data = opensync.Data()

        self.sink.commit(self.data, self.info, chg, self.ctx)
        return chg.uid

    def delete(self, LUID):
        chg = opensync.Change()
        chg.uid = LUID
        # change.format = "plain"
        # change.objtype = "data"
        chg.changetype = opensync.CHANGE_DELETED
        self.sink.commit(self.data, self.info, chg, self.ctx)

    def finish(self):
        self.uids = None
        self.sink.disconnect(self.data, self.info, self.ctx)

    def get_UID(self):
        return "foobar"

class Callbacks(opensync.ContextCallbacks):
    def __init__(self, dp):
        self.dp = dp

    def callback(self, err):
        pass

    def changes(self, change):
        # Clearly we only support opensync plugins that return VCARD data :)
        data = str(change.data.data)[:-1]
        contact = Contact.Contact(None)
        contact.set_from_vcard_string(data)
        # contact.set_mtime(change.data.revision)
        contact.set_UID(change.uid)
        self.dp.uids[change.uid] = contact

    def warning(self, err):
        logd("warning: %s" % err)

