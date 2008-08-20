from common import *

import traceback
import gobject
import threading

import gtk
gtk.gdk.threads_init()

import conduit.datatypes.File as File
import conduit.datatypes.Video as Video
import conduit.datatypes.Audio as Audio
import conduit.utils as Utils
import conduit.Exceptions as Exceptions

test = SimpleTest()
tc = test.type_converter

ok("Video Conversion exists", tc.conversion_exists("file","file/video") == True)
ok("Audio Conversion exists", tc.conversion_exists("file","file/audio") == True)

TEST = (
#name.list          #encodings to test  #available encodings
("video",           ('divx','flv','ogg'),          Video.PRESET_ENCODINGS      ),
("audio",           ('ogg',),           Audio.PRESET_ENCODINGS      ),
)

def convert():    
    for name, test_encodings, all_encodings in TEST:
        files = get_external_resources(name)
        for description,uri in files.items():
            f = File.File(uri)
            ok("%s: File %s exists" % (name,uri), f.exists())
            for encoding in test_encodings:
                args = all_encodings[encoding]
                ok("%s: Testing encoding of %s -> %s" % (name,description,encoding), True)
                
                to_type = "file/%s?%s" % (name,Utils.encode_conversion_args(args))
                try:
                    newdata = tc.convert("file",to_type, f)
                    ok("%s: Conversion OK" % name, newdata != None and newdata.exists(), False)
                except Exceptions.ConversionError:
                    ok("%s: Conversion Failed" % name, False, False)
    finished()           
    mainloop.quit()
    return False

def idle_cb():
    threading.Thread(target=convert).start()

mainloop = gobject.MainLoop()
gobject.idle_add(idle_cb)
mainloop.run()




