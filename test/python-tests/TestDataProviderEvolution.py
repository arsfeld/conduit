#common sets up the conduit environment
from common import *

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
    test = SimpleTest(sinkName=name)
    config = {
        "sourceURI":    uri
    }
    test.configure(sink=config)
    
    #Check we get the correct uri
    dp = test.get_sink().module
    try:
        dp.refresh()
        ok("Got evolution source uri: %s" % uri,
            uri in [i[1] for i in dp.allSourceURIs]
            )
    except Exception, err:
        ok("Got evolution source uri: %s" % uri, False)
    
    newdata = newdata_func(None)
    test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safeLUID=None,
        data=newdata,
        name=name
        )

finished()


