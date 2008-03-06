#common sets up the conduit environment
from common import *
import conduit.Utils as Utils

import datetime
import os.path

#Test resizing an image 200wx100h
w,h = Utils.get_proportional_resize(100,None,200,100)
ok("Resized Image in one dimension OK", w==100 and h==50)
w,h = Utils.get_proportional_resize(None,1000,200,100)
ok("Resized Image in one dimension OK", w==2000 and h==1000)
w,h = Utils.get_proportional_resize(200,1000,200,100)
ok("Resized Image in both dimension OK", w==2000 and h==1000)
w,h = Utils.get_proportional_resize(2000,100,200,100)
ok("Resized Image in both dimension OK", w==2000 and h==1000)
w,h = Utils.get_proportional_resize(10,5,200,100)
ok("Resized Image in both dimension OK", w==10 and h==5)
ok("Resized Image returns integers", type(w)==int and type(h)==int)

ok("Test program installed finds sh", Utils.program_installed('sh'))
ok("Test program installed doesnt find foobar", Utils.program_installed('foobar') == False)

fileuri = Utils.new_tempfile("bla").get_local_uri()
ok("New tempfile: %s" % fileuri, os.path.isfile(fileuri))
tmpdiruri = Utils.new_tempdir()
ok("New tempdir: %s" % tmpdiruri, os.path.isdir(tmpdiruri))

ok("Unique list keep order", Utils.unique_list([1,1,2,2,3,3,5,5,4,4]) == [1,2,3,5,4])

s = Utils.random_string()
ok("Random string: %s" % s, len(s) > 0 and type(s) == str)
s = Utils.md5_string('Foo')
ok("md5 string: %s" % s, len(s) > 0 and type(s) == str)
s = Utils.uuid_string()
ok("uuid string: %s" % s, len(s) > 0 and type(s) == str)
s = Utils.get_user_string()
ok("user string: %s" % s, len(s) > 0 and type(s) == str)

ts = 0
dt = datetime.datetime(1970, 1, 1, 12, 0)
ok("Datetime to unix timestamp", Utils.datetime_get_timestamp(dt) == ts)
ok("Unix timestamp to datetime", Utils.datetime_from_timestamp(ts) == dt)

m = Utils.Memstats()
VmSize,VmRSS,VmStack = m.calculate()
ok("Memstats: size:%s rss:%s stack:%s" % (VmSize,VmRSS,VmStack), VmSize > 0 and VmRSS > 0 and VmStack > 0)

# Test the shiny command line executer
conv = Utils.CommandLineConverter()
conv.build_command("ls %s %s")
cmdok,output = conv.convert("/tmp","/dev/null",callback=None,save_output=True)

ok("Command executed ok", cmdok == True and len(output) > 0)

ok("Simple xml tag extractor", 
        Utils.xml_extract_value_from_tag("tag", "<tag>foo tag bar</tag>") == "foo tag bar")
ok("Simple xml tag extractor", 
        Utils.xml_extract_value_from_tag("tag", "<nottag>tag</nottag>") == None)


finished()
