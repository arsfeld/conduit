from OpensyncBase import ContactDataprovider, EventDataprovider

MODULES = {
    "OS_Evolution_Contact":   { "type": "dataprovider" },
    "OS_Evolution_Event":     { "type": "dataprovider" },
}

evo_config = """<config>
                    <address_path>default</address_path>
                    <calendar_path>default</calendar_path>
                    <tasks_path>default</tasks_path>
                </config>"""

class OS_Evolution_Contact(ContactDataprovider):
    pass

class OS_Evolution_Event(EventDataprovider):
    pass
