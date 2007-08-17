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
import conduit.datatypes.Event as Event

import md5

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


class BaseDataprovider(DataProvider.TwoWay):
    """
    Generic dataprovider for interfacing with OpenSync plugins
    """

    _module_type_ = "twoway"

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
        chg = self._object_to_change(obj)
        
        if overwrite == True or LUID != None:
            chg.uid = LUID
            chg.changetype = opensync.CHANGE_TYPE_MODIFIED
        else:
            chg.changetype = opensync.CHANGE_TYPE_ADDED

        self.sink.commit_change(self.data, self.info, chg, self.ctx)
        return chg.uid

    def delete(self, LUID):
        chg = opensync.Change()
        chg.uid = LUID
        chg.changetype = opensync.CHANGE_TYPE_DELETED
        self.sink.commit_change(self.data, self.info, chg, self.ctx)

    def finish(self):
        self.uids = None
        self.sink.disconnect(self.data, self.info, self.ctx)

    def get_UID(self):
        return "foobar"

    def convert(self, data, chgfrom, chgto):
        """ Invoke an opensync conversion plugin """
        if chgfrom == chgto:
            return data

        formatfrom = self.formats.find_objformat(chgfrom)
        formatto = self.formats.find_objformat(chgto)
        converter = self.formats.find_converter(formatfrom, formatto)
        return converter.invoke(data, "")

    def _change_to_object(self, change):
        """ Map from an opensync data object to a Conduit data object """
        raise NotImplementedError

    def _object_to_change(self, obj):
        """ Map from a Conduit data object to an opensync data object """
        raise NotImplementedError

    def _get_hash(self, change):
        myhash = change.hash
        if myhash == None or len(myhash) == 0:
            return md5.md5(change.data.data).hexdigest()

class Callbacks(opensync.ContextCallbacks):
    def __init__(self, dp):
        self.dp = dp

    def callback(self, err):
        pass

    def changes(self, change):
        self.dp.uids[change.uid] = self.dp._change_to_object(change)

    def warning(self, err):
        logd("warning: %s" % err)


class ContactDataprovider(BaseDataprovider):

    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"
    _osync_type_ = "vcard30"

    def _change_to_object(self, change):
        uid = change.uid
        # FIXME: Shouldn't need to trim the data!
        data = str(change.data.data)[:-1]
        logd(self._get_hash(change))
        contact = Contact.Contact(None)
        contact.set_from_vcard_string(data)
        # contact.set_mtime(...)
        contact.set_UID(change.uid)
        return contact

    def _object_to_change(self, obj):
        chg = opensync.Change()
        chg.format = "vcard30"
        chg.objtype = "data"
        format = self.formats.find_objformat("vcard30")
        vcard = str(obj.get_vcard_string())
        chg.data = opensync.Data(vcard, format)
        return chg

class EventDataprovider(BaseDataprovider):

    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"
    _osync_type_ = "vevent20"

    def _change_to_object(self, change):
        uid = change.uid
        # FIXME: Shouldn't need to trim the data!
        data = str(change.data.data)[:-1]
        
        event = Event.Event(None)
        event.set_from_ical_string(data)
        event.set_UID(uid)
        # event.set_mtime(...)
        return event

    def _object_to_change(self, obj):
        chg = opensync.Change()
        chg.format = "vevent20"
        chg.objtype = "data"
        format = self.formats.find_objformat("vevent20")
        vcard = str(obj.get_ical_string())
        chg.data = opensync.Data(vcard, format)
        return chg


class OpenSyncFactory(DataProvider.DataProviderFactory):
    types = {
        "contact": ContactDataprovider,
        "event":   EventDataprovider,
    }

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
            "sink":           sink,
            "data":           data,
            "info":           info,
            "formats":        self.formats,
        }
        name = "opensync-" + plugin.name + "-" + sink.name

        if sink.name in self.types:
            dataprovider = type(name, (self.types[sink.name], ), fields)

            key = self.emit_added(
                dataprovider, 
                (name, ), 
                category
            )

