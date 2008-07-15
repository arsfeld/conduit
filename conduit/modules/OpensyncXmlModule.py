import re
import logging
log = logging.getLogger("modules.Converter")

import conduit.utils as Utils
import conduit.TypeConverter as TypeConverter
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Text as Text
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.datatypes.Note as Note
import conduit.datatypes.Setting as Setting

MODULES = {
        "OSContactConverter" :    { "type": "converter" },
}

class OSContactConverter(TypeConverter.Converter):
    def __init__(self):
        self.conversions =  {
                            "os2contact,contact": self.os2contact_to_contact,
                            "contact,os2contact": self.contact_to_os2contact,
        }

    def os2contact_to_contact(self, incoming, **kwargs):
        pass

    def contact_to_os2contact(self, incoming, **kwargs):
        pass
