#common sets up the conduit environment
from common import *
import conduit.datatypes.Contact as Contact
import conduit.utils as Utils
import conduit.Exceptions as Exceptions

if not is_online():
    skip()
    
SAFE_CONTACT_ID="http://www.google.com/m8/feeds/contacts/conduitproject%40gmail.com/base/89c42ac889d80b8"

vcfData="""
BEGIN:VCARD
VERSION:3.0
FN:Random Person
N:Person;A;Random;;
EMAIL;TYPE=INTERNET:%s@email.com
END:VCARD"""

#setup the test
test = SimpleTest(sinkName="ContactsTwoWay")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject@gmail.com"),
    "password":     os.environ["TEST_PASSWORD"],
}
test.configure(sink=config)
google = test.get_sink().module

#Log in
try:
    google.refresh()
    ok("Logged in", google.loggedIn == True)
except Exception, err:
    ok("Logged in (%s)" % err, False) 

#make a new contact with a random email address (so it doesnt conflict)
contact = Contact.parse_vcf(vcfData % Utils.random_string())[0]
test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safeLUID=SAFE_CONTACT_ID,
        data=contact,
        name="contact"
        )

#check we get a conflict if we put a contact with a known existing email address
#FIXME: We should actually automatically resolve this conflict...
contact = new_contact(None)
try:
    google.put(contact, False)
    ok("Detected duplicate email", False)
except Exceptions.SynchronizeConflictError:
    ok("Detected duplicate email", True)

finished()
