import conduit
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.HalFactory as HalFactory
from OpensyncBase import ContactDataprovider, EventDataprovider

MODULES = {
    "OS_SynceFactory" :        { "type": "dataprovider-factory" },
}


class OS_SynceFactory(HalFactory.HalFactory):

    def is_interesting(self, device, props):
        if props.has_key("info.parent") and props.has_key("info.parent")!="":
            prop2 = self._get_properties(props["info.parent"])
            if prop2.has_key("info.linux.driver") and prop2["info.linux.driver"]=="rndis_host":
               #    if "usb.interface.class" in props and props["usb.interface.class"] == 239:
               return True
        return False

    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    "HTC Phone",
                    "multimedia-player-ipod-video-white",
                    udi)

    def get_dataproviders(self, device, **kwargs):
        return [OS_Synce_Contact, OS_Synce_Event, OS_Synce_Todo]


class OS_Synce_Contact(ContactDataprovider):

    _name_ = "Synce Contacts"
    _description_ = "Sync your devices contacts"
    _os_name_ = "synce-plugin"
    _os_sink_ = "contact"

    def _get_config(self):
        return ""


class OS_Synce_Event(EventDataprovider):

    _name_ = "Synce Events"
    _description_ = "Sync your devices events"
    _os_name_ = "synce-plugin"
    _os_sink_ = "event"

    def _get_config(self):
        return ""


class OS_Synce_Todo(EventDataprovider):

    _name_ = "Synce Todo"
    _description_ = "Sync your devices tasks"
    _os_name_ = "synce-plugin"
    _os_sink_ = "todo"

    def _get_config(self):
        return ""

