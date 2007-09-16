#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File
import conduit.datatypes.Note as Note
import conduit.Utils as Utils

import random
import datetime
import traceback

#setup the test
test = SimpleTest(sinkName="TomboyNoteTwoWay")
tomboy = test.get_sink().module

try:
    tomboy.refresh()
    ok("Refresh Tomboy", True)
except Exception, err:
    ok("Refresh Tomboy (%s)" % err, False) 

notes = tomboy.get_all()
num = len(notes)
ok("Got all notes (%s)" % num, num > 1)

#Get a note and check its valid
idx = random.randint(0,num)
note = tomboy.get(notes[idx])
ok("Got note #%s" % idx, note != None)
ok("Got note title (%s)" % note.title, len(note.title) > 0)
ok("Got note contents", len(note.contents) > 0)
ok("Got note raw xml", len(note.raw) > 0)

#make a new note
newnote = Note.Note(
                    title="Conduit-"+Utils.random_string(),
                    mtime=datetime.datetime.today(),
                    contents="Conduit Test Note"
                    )
try:
    uid = tomboy.put(newnote,False)
    print "uid", uid
    ok("Put new note (%s)" % uid, uid != None)
except Exception, err:
    traceback.print_exc()
    ok("Put new note: %s" % err, False)

#modify the note and replace the old one
teststr = Utils.random_string()
newnote.contents += teststr
try:
    i = tomboy.put(newnote, True, uid)
    ok("Overwrite the note", i == uid)
except:
    ok("Overwrite the note", False)

#check the content was replace correctly
try:
    tomboy._get_note(uid).contents.index(teststr)
    ok("Note was overwritten correctly", True)
except:
    traceback.print_exc()
    ok("Note was overwritten correctly", False)

#Try and overwrite the note with an older version. Check it conflicts
olddate = datetime.datetime.fromtimestamp(0)
newnote = tomboy._get_note(uid)
newnote.set_mtime(olddate)
try:
    tomboy.put(newnote, False, uid)
    ok("Oldnote conflicts with newnote", False)
except Exceptions.SynchronizeConflictError, err:
    comp = err.comparison
    ok("Oldnote conflicts with newnote. Comparison: %s" % comp, comp == conduit.datatypes.COMPARISON_OLDER)

#remove the note
try:
    tomboy.delete(uid)
    ok("Deleted note (%s)" % uid, tomboy.remoteTomboy.NoteExists(uid) == False)
except:
    ok("Deleted note (%s)" % uid, False)

finished()
