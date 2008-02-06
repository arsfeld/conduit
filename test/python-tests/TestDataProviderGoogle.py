#common sets up the conduit environment
from common import *

import conduit.datatypes.Event as Event
import conduit.Utils as Utils

import random

SAFE_CALENDAR_NAME="Conduit Project"
SAFE_EVENT_UID="cee1p5i0ta73dfgjcn9l94allg@google.com"
MAX_YOUTUBE_VIDEOS=5

if not is_online():
    skip()

#setup the test
test = SimpleTest(sinkName="GoogleCalendarTwoWay")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject@gmail.com"),
    "password":     os.environ["TEST_PASSWORD"],
    "selectedCalendarURI"   :   "conduitproject%40gmail.com",
    "selectedCalendarName"  :   SAFE_CALENDAR_NAME,
}
test.configure(sink=config)
google = test.get_sink().module

#check we can get the calendar
found = False
for cal in google._get_all_calendars():
    if cal.get_name() == SAFE_CALENDAR_NAME:
        found = True
        break
        
ok("Found calendar: '%s'" % SAFE_CALENDAR_NAME, found)    

#make a simple event
hour=random.randint(12,24)
ics="""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PYVOBJECT//NONSGML Version 1//EN
BEGIN:VEVENT
DTSTART:2008%(month)02d%(day)02dT%(hour)02d0000Z
DTEND:2008%(month)02d%(day)02dT%(end)02d0000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR""" % {    "month" :   random.randint(1,12),
                        "day"   :   random.randint(1,28),
                        "hour"  :   hour,
                        "end"   :   hour+1}

event = Event.Event()
event.set_from_ical_string(ics)
test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=False,
        safeLUID=SAFE_EVENT_UID,
        data=event,
        name="event"
        )
        
#Now a very simple youtube test...
test = SimpleTest(sourceName="YouTubeSource")
config = {
    "max_downloads" :   MAX_YOUTUBE_VIDEOS
}
test.configure(source=config)
youtube = test.get_source().module

try:
    youtube.refresh()
    ok("Refresh youtube", True)
except Exception, err:
    ok("Refresh youtube (%s)" % err, False) 

videos = youtube.get_all()
num = len(videos)
ok("Got %s videos" % num, num == MAX_YOUTUBE_VIDEOS)

finished()
