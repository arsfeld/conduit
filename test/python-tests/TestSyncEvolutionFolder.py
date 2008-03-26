#common sets up the conduit environment
from common import *
import conduit.utils as Utils

SAFE_TASK_URI="file:///home/john/.evolution/tasks/local/1204062882.7099.2@nzjrs-desktop"
SAFE_MEMO_URI="file:///home/john/.evolution/memos/local/1204062871.7099.1@nzjrs-desktop"
SAFE_CALENDAR_URI="file:///home/john/.evolution/calendar/local/1204062855.7099.0@nzjrs-desktop"
SAFE_CONTACT_URI="file:///home/john/.evolution/addressbook/local/1203075663.31342.0@nzjrs-desktop"


TESTS = (
#uri,               #newdata_func,          #name
(SAFE_MEMO_URI,         new_note,               "EvoMemoTwoWay"),
(SAFE_CONTACT_URI,      new_contact,            "EvoContactTwoWay"),
(SAFE_CALENDAR_URI,     new_event,              "EvoCalendarTwoWay"),
(SAFE_TASK_URI,         new_event,              "EvoTasksTwoWay"),
)

for uri, newdata_func, name in TESTS:
    #setup the conduit
    test = SimpleSyncTest()
    test.prepare(
            source=test.get_dataprovider(name),
            sink=test.get_dataprovider("FolderTwoWay")
            )
    test.set_two_way_policy({"conflict":"ask","deleted":"ask"})

    #configure the source and sink
    test.configure(
            source={"sourceURI":uri},
            sink={"folder":"file://"+Utils.new_tempdir()}
            )
    test.set_two_way_sync(True)

    a = test.get_source_count()
    ok("%s: %s items to sync" % (name, a), a > 0)
    
    #sync
    test.sync()
    abort,error,conflict = test.get_sync_result()
    ok("%s: sync completed" % name, abort == False and error == False and conflict == False)

finished()
