import conduit
from OpensyncBase import ContactDataprovider, EventDataprovider

MODULES = {
#    "OS_SynceFactory" :        { "type": "dataprovider-factory" },
}


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

