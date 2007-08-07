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

try:
    import opensync
    MODULES = {
        "OpenSyncFactory":        { "type": "dataprovider-factory" },
    }
except:
    pass

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
            "_in_type_":      "contact",
            "_out_type_":     "contact",
            "_icon_":         "contact-new",
            "sink":           sink,
            "data":           data,
            "info":           info,
            "formats":        self.formats,
        }
        name = "opensync-" + plugin.name + "-" + sink.name
        dataprovider = type(name, (ContactDataprovider, ), fields)

        key = self.emit_added(
                                  dataprovider, 
                                  (name, ), 
                                  category
                             )


class BaseDataprovider(DataProvider.TwoWay):
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
            chg.changetype = opensync.CHANGE_TYPE_MODIFIED
        else:
            chg.changetype = opensync.CHANGE_TYPE_ADDED

        chg.format = "vcard30"
        chg.objtype = "data"

        chg.data = self.object_to_change(obj)

        self.sink.commit_change(self.data, self.info, chg, self.ctx)
        return chg.uid

    def delete(self, LUID):
        chg = opensync.Change()
        chg.uid = LUID
        # change.format = "plain"
        # change.objtype = "data"
        chg.changetype = opensync.CHANGE_TYPE_DELETED
        self.sink.commit_change(self.data, self.info, chg, self.ctx)

    def finish(self):
        self.uids = None
        self.sink.disconnect(self.data, self.info, self.ctx)

    def get_UID(self):
        return "foobar"

    def change_to_object(self, change):
        """ Map from an opensync data object to a Conduit data object """
        raise NotImplementedError

    def object_to_change(self, obj):
        """ Map from a Conduit data object to an opensync data object """
        raise NotImplementedError


class Callbacks(opensync.ContextCallbacks):
    def __init__(self, dp):
        self.dp = dp

    def callback(self, err):
        pass

    def changes(self, change):
        self.dp.uids[change.uid] = self.dp.change_to_object(change)

    def warning(self, err):
        logd("warning: %s" % err)


class ContactDataprovider(BaseDataprovider):

    _in_type_ = "contact"
    _out_type_ = "contact"

    def change_to_object(self, change):
        change = obj.change
        uid = change.uid
        # FIXME: Shouldn't need to trim the data!
        data = str(change.data.data)[:-1]

        contact = Contact.Contact(None)
        contact.set_from_vcard_string(data)
        # contact.set_mtime(change.data.revision)
        contact.set_UID(change.uid)
        return contact

    def object_to_change(self, obj):
        format = self.formats.find_objformat("vcard30")
        vcard = str(obj.get_vcard_string())
        data = opensync.Data(vcard, format)


class EventDataprovider(BaseDataprovider):

    _in_type_ = "event"
    _out_type_ = "event"

    def change_to_object(self, change):
        change = obj.change
        uid = change.uid
        # FIXME: Shouldn't need to trim the data!
        data = str(change.data.data)[:-1]

        contact = Contact.Contact(None)
        contact.set_from_vcard_string(data)
        # contact.set_mtime(change.data.revision)
        contact.set_UID(change.uid)
        return contact

    def object_to_change(self, obj):
        format = self.formats.find_objformat("vcard30")
        vcard = str(obj.get_vcard_string())
        data = opensync.Data(vcard, format)

