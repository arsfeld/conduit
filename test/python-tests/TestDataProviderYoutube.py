#common sets up the conduit environment
from common import *

import conduit.datatypes.Event as Event
import conduit.utils as Utils

import random

SAFE_CALENDAR_NAME="Conduit Project"
SAFE_EVENT_UID="2bh7mbagsc880g64qaps06tbp4@google.com"
MAX_YOUTUBE_VIDEOS=5

if not is_online():
    skip()

#-------------------------------------------------------------------------------
# Youtube
#-------------------------------------------------------------------------------
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
