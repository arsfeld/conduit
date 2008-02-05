#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.Utils as Utils

if not is_online():
    skip()
    
#setup the test
test = SimpleTest(sinkName="GmailEmailTwoWay")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject"),
    "password":     os.environ["TEST_PASSWORD"]
}
test.configure(sink=config)

#get the module directly so we can call some special functions on it
gmail = test.get_sink().module

#Log in
try:
    gmail.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

e = new_email(None)
test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=False,
        safeLUID='110fb3737234b8de',
        data=e,
        name="email"
        )
        
#Now test the contact source
test = SimpleTest(sinkName="GmailContactSource")
test.configure(sink=config)
test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=False,
        safeLUID="john.stowers@gmail.com",
        data=None,
        name="contact"
        )

finished()

