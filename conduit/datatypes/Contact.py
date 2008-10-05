import vobject 
import conduit.datatypes.DataType as DataType
def parse_vcf(string):
    """
    Parses a vcf string, potentially containing many vcards
    @returns: A list of Contacts
    """
    contacts = []
    for vobj in vobject.readComponents(string):
        if vobj.behavior == vobject.vcard.VCard3_0:
            contacts.append(Contact(vcard=vobj))
    return contacts
    
class Contact(DataType.DataType):
    """
    Very basic contact representation
    @keyword vcard: A vobject.vcard.VCard3_0 instance
    """
    _name_ = "contact"
    def __init__(self, **kwargs):
        DataType.DataType.__init__(self)
        self.vcard = kwargs.get('vcard',vobject.vCard())
        self.set_name(**kwargs)

    def set_from_vcard_string(self, string):
        self.vcard = vobject.readOne(string)

    def get_vcard_string(self, version=2.1):
        for prop in ('fn', 'n'):
	    if prop not in self.vcard.contents:
	        self.vcard.add(prop)
        return self.vcard.serialize()
        
    def get_emails(self):
        emails = []
        if 'email' in self.vcard.contents:
            for email in self.vcard.contents['email']:
                emails.append(email.value)
        return emails
        
    def get_name(self):
        #In order of preference, 1)formatted name, 2)name, 3)""
        #FIXME: Return dict of formattedName, givenName, familyName, etc
        for attr in [self.vcard.fn, self.vcard.n]:
            #because str() on a vobject.vcard.Name pads with whitespace
            name = str(attr.value).strip()
            if len(name) > 0:
                return name
        return ""
        
    def set_name(self, **kwargs):
        #vcards must have one, and only one N and FN
        fn = kwargs.get("formattedName","")
        try:
            self.vcard.fn
        except AttributeError:
            self.vcard.add('fn')
        if fn:
            self.vcard.fn.value = fn

        g = kwargs.get("givenName","")
        f = kwargs.get("familyName","")
        try:
            self.vcard.n
        except AttributeError:
            self.vcard.add('n')
        if f or g:
            self.vcard.n.value = vobject.vcard.Name(family=f,given=g)

    def set_emails(self, *args):
        for address in args:
            email = self.vcard.add('email')
            email.value = address
            email.type_param = 'INTERNET'
        
    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['vcard'] = self.get_vcard_string()
        return data

    def __setstate__(self, data):
        self.set_from_vcard_string(data['vcard'])
        DataType.DataType.__setstate__(self, data)

    def __str__(self):
        return "Name: %s" % self.get_name()
        
    def get_hash(self):
        return str(hash(self.get_vcard_string()))
    

