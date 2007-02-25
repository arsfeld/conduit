#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.Utils as Utils

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)
type_converter = TypeConverter(model)

USERNAME="%s@gmail.com" % os.environ['TEST_USERNAME']
PASSWORD="%s" % os.environ['TEST_PASSWORD']

gmail = model.get_new_module_instance("GmailEmailTwoWay").module
gmail.username = USERNAME
gmail.password = PASSWORD

#Log in
try:
    gmail.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

#Send a remote file
f = File.File("ssh://root@www.greenbirdsystems.com/root/sync/tests/new/newest")
try:
    email = type_converter.convert("file","email",f)
    ok("Convert file to email (%s)" % email.get_open_URI(), True)
    uid = gmail.put(email, True)
    ok("Save a file to Gmail (UID:%s) "% uid, True)
except Exception, err:
    ok("Save a file to Gmail (%s)" % err, False)

#Send an email to myself
subject = Utils.random_string()
email = Email.Email(
                None,
                to="",
                subject=subject,
                content="TestGmail.py"
                )
try:
    uid = gmail.put(email, True)
    ok("Sent Email (UID:%s) "% uid, True)
except Exception, err:
    ok("Sent Email (%s)" % err, False)
                
