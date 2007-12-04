"""
Interfaces for inter-operation with opensync

Copyright: John Stowers, 2006
License: GPLv2
"""
import md5
import logging
log = logging.getLogger("dataproviders.Opensync")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
from conduit.datatypes import Rid
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event

try:
    import opensync
except ImportError:
    raise conduit.Exceptions.NotSupportedError

# Create a Format Environment and load plugins in to it
formats = opensync.FormatEnv()
formats.load_plugins()

# Create a Plugins Environment and load plugins in to it
plugins = opensync.PluginEnv()
plugins.load()

class BaseDataprovider(DataProvider.TwoWay):
    """
    Generic dataprovider for interfacing with OpenSync plugins

    Maps all Conduit sync calls onto the OpenSync code. HAL and other
    integration work is left to the DPs that extend this base class.
    """

    _module_type_ = "twoway"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        
        self.info = None
        self.data = None
        self.sink = None
        self.ctx = None

        for plugin in plugins.plugins:
            print plugin.name
            if plugin.name == self._os_name_:
                self.info = opensync.PluginInfo()
                self.info.set_config(self._get_config())
                self.info.set_format_env(formats)

                self.data = plugin.initialize(self.info)
                plugin.discover(self.data, self.info)

                for sink in self.info.objtypes:
                    print sink.name
                    if sink.name == self._os_sink_:
                        self.sink = sink
                        self.info.sink = sink

        assert self.info and self.sink

        self.ctx = opensync.Context()
        self.ctx.set_callback_object(Callbacks(self))
        self.uids = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.uids = {}
        self.sink.connect(self.data, self.info, self.ctx)

    def get_all(self):
        self.uids = {}
        self.sink.get_changes(self.data, self.info, self.ctx)
        return list(self.uids.keys())

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self.uids[LUID]

    def put(self, obj, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)
        chg = self._object_to_change(obj)
        
        if overwrite == True and LUID != None:
            chg.uid = LUID
            chg.changetype = opensync.CHANGE_TYPE_MODIFIED
        else:
            chg.changetype = opensync.CHANGE_TYPE_ADDED

        self.sink.commit_change(self.data, self.info, chg, self.ctx)
        return Rid(uid=chg.uid, hash=self._get_hash(chg))

    def delete(self, LUID):
        print type(LUID)
        DataProvider.TwoWay.delete(self, LUID)
        chg = opensync.Change()
        chg.uid = LUID
        chg.changetype = opensync.CHANGE_TYPE_DELETED
        self.sink.commit_change(self.data, self.info, chg, self.ctx)

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        self.uids = None
        self.sink.disconnect(self.data, self.info, self.ctx)

    def get_UID(self):
        return "foobar"

    def _convert(self, data, chgfrom, chgto):
        """ 
        Invoke an opensync conversion plugin 
        """
        if chgfrom == chgto:
            return data

        formatfrom = formats.find_objformat(chgfrom)
        formatto = formats.find_objformat(chgto)
        converter = formats.find_converter(formatfrom, formatto)
        return converter.invoke(data, "")

    def _get_hash(self, change):
        """
        If it's valid, return an osync change hash.
        Otherwise, generate a new one.
        """
        myhash = change.hash
        if myhash == None or len(myhash) == 0:
            return md5.md5(change.data.data).hexdigest()

    def _change_to_object(self, change):
        """
        Map from an opensync data object to a Conduit data object 
        """
        raise NotImplementedError

    def _object_to_change(self, obj):
        """ 
        Map from a Conduit data object to an opensync data object 
        """
        raise NotImplementedError

    def _get_config(self):
        """ 
        Generate the config that opensync needs to use this endpoint
        """
        raise NotImplementedError


class Callbacks(opensync.ContextCallbacks):
    """
    The OpenSync bindings call back into this function as changes are received
    from the other dataprovider. As they are received, we updated the uids dict.

    Would it be dirty to merge this with the dataprovider base? I think so.
    """

    def __init__(self, dp):
        self.dp = dp

    def callback(self, err):
        log.warn(err)

    def changes(self, change):
        self.dp.uids[change.uid] = self.dp._change_to_object(change)

    def warning(self, warning):
        log.warn(warning)


class ContactDataprovider(BaseDataprovider):
    """
    Implement mappings between Conduit vcard and OS vcard
    """

    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"
    _osync_type_ = "vcard30"

    def _change_to_object(self, change):
        uid = change.uid
        # FIXME: Shouldn't need to trim the data!
        data = str(change.data.data)[:-1]
        contact = Contact.Contact(None)
        contact.set_UID(change.uid)
        contact.set_from_vcard_string(data)
        # contact.set_hash(self._get_hash(change))
        # contact.set_mtime(...)
        return contact

    def _object_to_change(self, obj):
        chg = opensync.Change()
        chg.format = "vcard30"
        chg.objtype = "data"
        format = formats.find_objformat("vcard30")
        vcard = str(obj.get_vcard_string())
        chg.data = opensync.Data(vcard, format)
        return chg

class EventDataprovider(BaseDataprovider):
    """
    Implement mappings between Conduit vevent and OS vevent
    """

    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"
    _osync_type_ = "vevent20"

    def _change_to_object(self, change):
        uid = change.uid
        # FIXME: Shouldn't need to trim the data!
        data = str(change.data.data)[:-1]
        event = Event.Event(None)
        event.set_UID(uid)
        event.set_from_ical_string(data)
        # event.set_hash(self._get_hash(change))
        # event.set_mtime(...)
        return event

    def _object_to_change(self, obj):
        chg = opensync.Change()
        chg.format = "vevent20"
        chg.objtype = "data"
        format = formats.find_objformat("vevent20")
        vcard = str(obj.get_ical_string())
        chg.data = opensync.Data(vcard, format)
        return chg


