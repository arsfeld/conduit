import conduit
from OpensyncBase import ContactDataprovider, EventDataprovider

MODULES = {
    "OS_Evolution_Contact":   { "type": "dataprovider" },
    "OS_Evolution_Event":     { "type": "dataprovider" },
#    "OS_Evolution_Todo":     { "type": "dataprovider" },
}


class OS_Evolution_Contact(ContactDataprovider):

    _name_ = "Evolution Contacts"
    _description_ = "Sync your Evolution contacts"
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _os_name_ = "evo2-sync"
    _os_sink_ = "contact"

    def _get_config(self):
        config = """<config>
                        <address_path>default</address_path>
                        <calendar_path>default</calendar_path>
                        <tasks_path>default</tasks_path>
                    </config>"""
        return config


class OS_Evolution_Event(EventDataprovider):

    _name_ = "Evolution Events"
    _description_ = "Sync your Evolution events"
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _os_name_ = "evo2-sync"
    _os_sink_ = "event"

    def _get_config(self):
        config = """<config>
                        <address_path>default</address_path>
                        <calendar_path>default</calendar_path>
                        <tasks_path>default</tasks_path>
                    </config>"""
        return config


class OS_Evolution_Todo(EventDataprovider):

    _name_ = "Evolution Todo"
    _description_ = "Sync your Evolution tasks"
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _os_name_ = "evo2-sync"
    _os_sink_ = "todo"

    def _get_config(self):
        config = """<config>
                        <address_path>default</address_path>
                        <calendar_path>default</calendar_path>
                        <tasks_path>default</tasks_path>
                    </config>"""
        return config
