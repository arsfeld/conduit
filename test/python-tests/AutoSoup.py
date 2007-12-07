"""
  This is part of the automatic test case generator

  This file contains the basic building blocks of our tests - dataproviders and data.
"""

#common sets up the conduit environment
from common import *

# import any datatypes that are needed
import conduit.datatypes.File as File
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Note as Note

# import any dp's that we'll need to wrap
from conduit.modules import iPodModule

def dataprovider(datatype, **kwargs):
    """ Encapsulate a prep_... function in a class """
    def _(func):
        class Souplet(object):
            _datatype_ = datatype
            _name_ = func.__name__
            def instance(self, host):
                return func(host)
            def __str__(self):
                return self._name_
        return Souplet
    return _

def data(datatype, weight, **kwargs):
    def _(func):
        class Datalet(object):
            _datatype_ = datatype
            _weight_ = weight
            _name_ = func.__name__
            def get(self):
                return func()
            def __str__(self):
                return self._name_
        return Datalet
    return _

@data("contact", 5)
def objset_contacts():
    """
    Return a sample of contact objects
    """
    objs = []
    vcards = get_files_from_data_dir("*.vcard")
    for i in range(0, len(vcards)):
        c = Contact.Contact()
        c.set_from_vcard_string( read_data_file(vcards[i]) )
        objs.append(c)
    ok("Got %d sample contacts" % len(objs), len(objs) > 0)
    return objs

@data("event", 5)
def objset_events():
    """
    Return a sample of event objects
    """
    objs = []
    icals = get_files_from_data_dir("*.ical")
    for i in range(0, len(icals)):
        c = Event.Event(icals[i])
        c.set_from_ical_string( read_data_file(icals[i]) )
        objs.append(c)
    ok("Got %d sample events" % len(objs), len(objs) > 0)
    return objs

@data("note", 5)
def objset_notes():
    """
    Return a sample of note objects
    """
    objs = []
    notes = get_files_from_data_dir("*.tomboy")
    for i in range(0, len(notes)):
        n = Note.Note(title="Note-" + Utils.random_string())
        n.content = read_data_file(notes[i])
        n.raw = read_data_file(notes[i])
        objs.append(n)
    ok("Got %d sample notes" % len(objs), len(objs) > 0)
    return objs

@data("file", 1)
def objset_files():
    """
    Return a sample of file objects
    """
    objs = [File.File(f) for f in get_files_from_data_dir("*")]
    ok("Got %d sample contacts" % len(objs), len(objs) > 0)
    return objs

@dataprovider("event")
def prep_ipod_calendar(host):
    source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod calendar " + Utils.random_string())
    if not os.path.exists(source_folder):
        os.mkdir(source_folder)
    return host.wrap_dataprovider( iPodModule.IPodCalendarTwoWay(source_folder, "") )

@dataprovider("contact")
def prep_ipod_contacts(host):
    source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod contacts " + Utils.random_string())
    if not os.path.exists(source_folder):
        os.mkdir(source_folder)
    return host.wrap_dataprovider( iPodModule.IPodContactsTwoWay(source_folder, "") )

@dataprovider("note")
def prep_ipod_notes(host):
    source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod notes " + Utils.random_string())
    if not os.path.exists(source_folder):
        os.mkdir(source_folder)
    return host.wrap_dataprovider( iPodModule.IPodNoteTwoWay(source_folder, "") )

@dataprovider("event")
def prep_folder_calendar(host):
    sink_folder = os.path.join(os.environ['TEST_DIRECTORY'], "folder calendar " + Utils.random_string())
    if not os.path.exists(sink_folder):
        os.mkdir(sink_folder)

    dp = host.get_dataprovider("FolderTwoWay")
    dp.module.set_configuration( { "folderGroupName": "calendar", "folder": "file://"+sink_folder } )
    return dp

@dataprovider("contact")
def prep_folder_contacts(host):
    sink_folder = os.path.join(os.environ['TEST_DIRECTORY'], "folder contacts " + Utils.random_string())
    if not os.path.exists(sink_folder):
        os.mkdir(sink_folder)

    dp = host.get_dataprovider("FolderTwoWay")
    dp.module.set_configuration( { "folderGroupName": "contacts", "folder": "file://"+sink_folder } )
    return dp

#@dataprovider("note")
#def prep_tomboy(host):
#    dp = host.get_dataprovider("TomboyTwoWay")
#    return dp

#@dataprovider("contact")
#def prep_evo_contacts(host):
#    dp = host.get_dataprovider("EvoContactTwoWay")
#    opts = dict(dp.module._addressBooks)
#    dp.module.set_configuration( { "sourceURI": opts["conduit-test"], } )
#    return dp

#@dataprovider("event")
#def prep_evo_calendar(host):
#    dp = host.get_dataprovider("EvoCalendarTwoWay")
#    opts = dict(dp.module._calendarURIs)
#    dp.module.set_configuration( { "sourceURI": opts["conduit-test"], } )
#    return dp

#@dataprovider("note")
#def prep_evo_memo(host):
#    dp = host.get_dataprovider("EvoMemoTwoWay")
#    opts = dict(dp.module._memoSources)
#    dp.module.set_configuration( { "sourceURI": opts["conduit-test"], } )
#    return dp

@dataprovider("contact")
def prep_opensync_evo_contact(host):
    dp = host.get_dataprovider("OS_Evolution_Contact")
    dp.module.set_configuration({"source": "Test"})
    return dp

@dataprovider("event")
def prep_opensync_evo_event(host):
    dp = host.get_dataprovider("OS_Evolution_Event")
    dp.module.set_configuration({"source": "Test"})
    return dp

