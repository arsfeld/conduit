#common sets up the conduit environment
from common import *

import conduit.datatypes.Note as Note
import conduit.utils as Utils

import random

#setup the test
test = SimpleTest(sinkName="TomboyNoteTwoWay")
tomboy = test.get_sink().module

#check if tomboy running
if not Utils.dbus_service_available(tomboy.TOMBOY_DBUS_IFACE):
    skip("tomboy not running")

try:
    tomboy.refresh()
    ok("Refresh Tomboy", True)
except Exception, err:
    ok("Refresh Tomboy (%s)" % err, False) 

notes = tomboy.get_all()
num = len(notes)
ok("Got all notes (%s)" % num, num > 1)

#Get a note and check its valid
idx = random.randint(0,num-1)
note = tomboy.get(notes[idx])
ok("Got note #%s" % idx, note != None)
ok("Got note title (%s)" % note.title, len(note.title) > 0)
ok("Got note contents", len(note.contents) > 0)

#make a new note
note = Note.Note(
                title="Conduit-"+Utils.random_string(),
                contents="Conduit Test Note"
                )
tnote = test.type_converter.convert("note","note/tomboy",note)

test.do_dataprovider_tests(
            supportsGet=True,
            supportsDelete=True,
            safeLUID=None,
            data=tnote,
            name="tomboy note"
            )

finished()
