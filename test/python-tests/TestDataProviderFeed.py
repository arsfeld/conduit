#common sets up the conduit environment
from common import *

if not is_online():
    skip()

#setup the test
test = SimpleTest(sourceName="RSSSource")

TESTS = (
    ("Photos",  "http://www.flickr.com/services/feeds/photos_public.gne?id=44124362632@N01&format=rss_200_enc"),
    ("Audio",   "http://www.lugradio.org/episodes.ogg.rss"),
    ("Video",   "http://telemusicvision.com/videos/tmv.rss")
)

for name,url in TESTS:
    ok("%s: Url %s" % (name,url), True)

    config = {
        "feedUrl":          url,
        "limit":            1,
        "downloadPhotos":   True,
        "downloadAudio":    True,
        "downloadVideo":    True
        }
    test.configure(source=config)
    dp = test.get_source().module

    try:
        dp.refresh()
        ok("%s: Downloaded feed ok" % name, True)
    except Exception, err:
        ok("%s: Downloaded feed (%s)" % (name,err), False)  

    try:
        enclosures = dp.get_all()
        ok("%s: Got enclosures" % name, len(enclosures) > 0)
    except Exception, err:
        ok("%s: Got enclosures (%s)" % (name,err), False)  

    try:
        f = dp.get(enclosures[0])
        ok("%s: Got a file" % name, f.exists())
    except Exception, err:
        ok("%s: Got a file (%s)" % (name,err), False) 
        
    try:
        dp.finish(True,True,True)
        config2 = dp.get_configuration()
        ok("%s: Got configuration" % name, config == config2)
    except Exception, err:
        ok("%s: Got configuration (%s)" % (name,err), False) 

finished()
