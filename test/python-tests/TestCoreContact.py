#common sets up the conduit environment
from common import *
import conduit.datatypes.Contact as Contact

vcfData="""
BEGIN:VCARD
VERSION:3.0
FN:
N:;;;;
EMAIL;TYPE=INTERNET:yws-flickr-unsubscribe@yahoogroups.com
END:VCARD
BEGIN:VCARD
VERSION:3.0
FN:
N:;;;;
EMAIL;TYPE=INTERNET:yws-flickr@yahoogroups.com
END:VCARD
BEGIN:VCARD
VERSION:3.0
FN:STA Travel Canterbury Uni
N:Uni;STA;Travel Canterbury;;
EMAIL;TYPE=INTERNET:cantiuni@branch.statravel.co.nz
END:VCARD"""

c = Contact.Contact()
ok("Created blank contact", len(c.get_vcard_string()) > 0)

c = Contact.Contact(formattedName="Im Cool", givenName="Steve", familyName="Cool")
ok("Created contact", len(c.get_vcard_string()) > 0)

contacts = Contact.parse_vcf(vcfData)
ok("Parsed vcf file (got %s vcards)" % len(contacts), len(contacts) == vcfData.count("BEGIN:VCARD"))

c = contacts[-1]
ok("Got vcard data", len(c.get_vcard_string()) > 0)
ok("Got email addresses", len(c.get_emails()) > 0)
ok("Got name", c.get_name() != None)

#now add email addresses
emails = ("foo@bar.com","baz@f")
numb4 = len(c.get_emails())
c.set_emails(*emails)
numAfta = len(c.get_emails())
ok("Added email addresses", numAfta == (numb4 | len(emails)))

finished()
