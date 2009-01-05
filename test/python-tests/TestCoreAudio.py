#common sets up the conduit environment
from common import *

import threading

import conduit
import conduit.datatypes.Audio as Audio

import gobject
import gtk
gtk.gdk.threads_init()


mainloop = gobject.MainLoop()

def run_audio_tests():
    try:
        #ok("Getting audio", True)
        #print 'Getting audio'
        audio = new_audio()
        #print 'Getting tags'
        media_tags = audio.get_media_tags()
        expected_tags = {'title': 'Title',
            'artist': 'Artist',
            'album': 'Album',
            'genre': 'Indie'}
        for name, value in expected_tags.iteritems():
            ok("Expected: %s = %s, Got %s = %s" % (name, expected_tags[name], name, name in media_tags and media_tags[name]),
                name in media_tags and expected_tags[name] == media_tags[name])
    except Exception, excp:
        print "Exception %s" % excp
    finally:
        mainloop.quit()


def idle_cb():
    threading.Thread(target=run_audio_tests).start()
    return False


gobject.idle_add(idle_cb)
mainloop.run()
finished()


