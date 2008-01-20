#common sets up the conduit environment
from common import *

import os.path
import shutil
import traceback

import conduit.modules.iPodModule as iPodModule
import conduit.Utils as Utils


#simulate an ipod
fakeIpodDir = Utils.new_tempdir()
ok("Created fake ipod at %s" % fakeIpodDir, os.path.exists(fakeIpodDir))

ipodNoteDp = iPodModule.IPodNoteTwoWay(fakeIpodDir,"")
ipodContactsDp = iPodModule.IPodContactsTwoWay(fakeIpodDir,"")
ipodCalendarDp = iPodModule.IPodCalendarTwoWay(fakeIpodDir,"")
ipodPhotoDp = iPodModule.IPodPhotoSink(fakeIpodDir,"")

#The ipod photo (and music AFAICT) require some initialization of 
#a skeleton database file. 
#This code, and example resources are taken from libgpod test suite
control_dir = os.path.join(fakeIpodDir,'iPod_Control')
photo_dir = os.path.join(control_dir, 'Photos')
shutil.copytree(
            os.path.join(get_data_dir(),'resources-ipod'),
            control_dir
            )
os.mkdir(photo_dir)
ipodPhotoDp._set_sysinfo("ModelNumStr", "MA450")

TESTS = (
#dpinstance,        #newdata_func,          #name                   #twoway
(ipodNoteDp,        new_note,               "IPodNoteTwoWay",       True),
(ipodContactsDp,    new_contact,            "IPodContactsTwoWay",   True),
(ipodCalendarDp,    new_event,              "IPodCalendarTwoWay",   True),
(ipodPhotoDp,       new_photo,              "IPodPhotoSink",        False),
)

for dp, newdata_func, name, istwoway in TESTS:
    test = SimpleTest()
    test.set_sink(
            test.wrap_dataprovider(dp)
            )
    
    newdata = newdata_func(None)
    test.do_dataprovider_tests(
        supportsGet=istwoway,
        supportsDelete=True,
        safeLUID=None,
        data=newdata,
        name="%s:%s" % (name,dp._in_type_)
        )

finished()
