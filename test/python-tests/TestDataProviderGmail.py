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
    "username":     os.environ.get("TEST_USERNAME","conduitproject@gmail.com"),
    "password":     os.environ["TEST_PASSWORD"],
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
        supportsGet=False,
        supportsDelete=False,
        safeLUID=None,
        data=e,
        name="email"
        )
                
finished()

