#common sets up the conduit environment
from common import *
import conduit.datatypes.Email as Email
import conduit.utils as Utils

e = Email.Email(
            to="me",
            subject="foo",
            content="bar"
            )

s = e.get_email_string()
ok("Email created ok", len(s) > 0)
ok("Email has no attachments", e.has_attachments() == False)

f = Utils.new_tempfile("I AM A TEXT FILE ATTACHMENT")
e.add_attachment(f.get_local_uri())
ok("Email has attachment", e.has_attachments() == True)

s2 = e.get_email_string()
ok("Email OK", len(s) > 0 and len(s2) > len(s))

h1 = e.get_hash()
e2 = Email.Email()
e2.set_from_email_string(s2)
h2 = e2.get_hash()
ok("Email serialize and deserialize OK", h1 == h2)

finished()
