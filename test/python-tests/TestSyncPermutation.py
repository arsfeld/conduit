import sys, inspect

#common sets up the conduit environment
from common import *

# import any datatypes that are needed
import conduit.datatypes.File as File
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event

# import any dp's that we'll need to wrap
from conduit.dataproviders import iPodModule

def objset_contacts():
    """
    Return a sample of contact objects
    """
    objs = []

    vcards = get_files_from_data_dir("*.vcard")
    for i in range(0, len(vcards)):
        c = Contact.Contact(vcards[i])
        c.set_from_vcard_string( read_data_file(vcards[i]) )
        objs.append(c)

    return objs

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
    return objs

def objset_files():
    """
    Return a sample of file objects
    """
    return [File.File(f) for f in get_files_from_data_dir("*")]

def convert(host, fromType, toType, data):
    newdata = None

    if fromType != toType:
        if host.type_converter.conversion_exists(fromType, toType):
            newdata = host.type_converter.convert(fromType, toType, data)
        else:
            newdata = None
            raise Exceptions.ConversionDoesntExistError
    else:
        newdata = data

    return newdata

def prep_ipod_calendar(host):
    source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod calendar " + Utils.random_string())
    if not os.path.exists(source_folder):
        os.mkdir(source_folder)

    return host.wrap_dataprovider( iPodModule.IPodCalendarTwoWay(source_folder, "") )

def prep_ipod_contacts(host):
    source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod contacts " + Utils.random_string())
    if not os.path.exists(source_folder):
        os.mkdir(source_folder)

    return host.wrap_dataprovider( iPodModule.IPodContactsTwoWay(source_folder, "") )

def prep_folder_calendar(host):
    sink_folder = os.path.join(os.environ['TEST_DIRECTORY'], "folder calendar " + Utils.random_string())
    if not os.path.exists(sink_folder):
        os.mkdir(sink_folder)

    dp = host.get_dataprovider("FolderTwoWay")
    dp.module.set_configuration( { "folderGroupName": "calendar", "folder": "file://"+sink_folder } )
    return dp

def prep_folder_contacts(host):
    sink_folder = os.path.join(os.environ['TEST_DIRECTORY'], "folder contacts " + Utils.random_string())
    if not os.path.exists(sink_folder):
        os.mkdir(sink_folder)

    dp = host.get_dataprovider("FolderTwoWay")
    dp.module.set_configuration( { "folderGroupName": "contacts", "folder": "file://"+sink_folder } )
    return dp

def test_delete_all(dp):
    """
    Delete any and all objects store on a dataprovider
    """
    ok("Can delete from this dp", dp.module_type == "twoway" or dp.module_type == "sink")

    uids = []

    dp.module.refresh()
    for uid in dp.module.get_all():
        dp.module.delete(uid)

    dp.module.refresh()
    ok("All objects deleted", dp.module.get_num_items() == 0)

def test_sync(host):
    """
    Wrapper around the sync method. It calls sync twice and checks for changes, which would
    indicate that the mappings db has become corrupted
    """
    # get the counts before we start
    a1 = host.get_source_count()
    b1 = host.get_sink_count()

    # after the first sync the counts should be the same on both sides
    a2, b2 = host.sync()
    ok("Sync worked (source had %s, source has %s, sink had %s, sink has %s)" % (a1, a2, b1, b2), a2==b2)

    # after the third sync nothing should have changed
    a3, b3 = host.sync()
    ok("Sync worked (source had %s, source has %s, sink had %s, sink has %s)" % (a2, a3, b2, b3), a3==b3)

    ok("Count didn't change between last 2 syncs", a2==a3 and b2==b3)

    return (a2-a1, b2-b1)

def test_add_data(host, dp, datatype, dataset):
    """
    Add some data to a dataprovider
    """
    objs = dataset()
    for i in range(0, len(objs)):
        obj = convert(host, datatype, dp.in_type, objs[i])
        dp.module.put(obj, True)

    dp.module.refresh()
    ok("Dataset loaded into source", dp.module.get_num_items() == len(objs)) 

    test_sync(host)

def test_modify_data(host, dp):
    pass

def test_delete_data(host, dp):
    pass

def test_clear(host):
    """
    Ensure that both dps are blank
    Run a combination of two way/one way and slow sync
    """
    test_delete_all(host.source)
    test_delete_all(host.sink)

    a, b = host.sync()
    ok("Sync worked (%s, %s)" % (a, b), a == 0 and b == 0)

def test_full(host, source, sink, datatype, dataset, twoway=True, slow=False):
    """
    Run all tests
    """
    ok("Beginning test run. Source: %s, Sink: %s, Datatype: %s, twoway: %s, Slow: %s" % (source, sink, datatype, twoway, slow), True)
 
    host.prepare(source, sink)
    host.set_two_way_sync(twoway)
    host.set_slow_sync(slow)

    # Ensure the dps are empty
    test_clear(host)
    test_add_data(host, host.source, datatype, dataset)
    test_modify_data(host, host.source)
    test_modify_data(host, host.sink)
    test_delete_data(host, host.source)
    test_delete_data(host, host.sink)

    # Same tests again, but inject at the sink.
    # Only makes sense in the twoway case
    if twoway:
        test_clear(host)
        test_add_data(host, host.sink, datatype, dataset)
        test_modify_data(host, host.sink)
        test_modify_data(host, host.source)
        test_delete_data(host, host.sink)
        test_delete_data(host, host.source)

    test_clear(host)

# Intialise sync management framework
host = SimpleSyncTest()
host.set_two_way_policy({
                "conflict"  :   "replace",
                "deleted"   :   "replace"}
                )
# It's hard to pick sane combinations of dps, so heres a little rules table to help out
# col 1 = weight. in sync folder <--> contact we need to use contact objects over file objects.
# col 2 = a function to call to get some data.
# As a bonus, reject combinations where col 1 is same (e.g. contact <--> event)
rules = {
    "contact":  (5, objset_contacts),
    "event":   (5, objset_events),
#    "note":     (5, objset_notes),
    "file":     (1, objset_files),
}

targets = []
combinations = []

# Cludge to gather all the dataprovider initialisers
for name in dir(sys.modules[__name__]):
    fn = getattr(sys.modules[__name__], name)
    if name[:5] == "prep_" and inspect.isfunction(fn):    
        targets.append( fn(host) )

# Cludge to match valid combinations of above
for source in targets:
    for sink in targets:
        if source != sink:
            in_type1 = source.in_type
            in_type2 = sink.in_type

            if in_type1 == in_type2:
                combinations.append( (source, sink, in_type1, rules[in_type1][1]) )
            elif rules[in_type1][0] > rules[in_type2][0]:
                combinations.append( (source, sink, in_type1, rules[in_type1][1]) )
            elif rules[in_type2][0] > rules[in_type1][0]:
                combinations.append( (source, sink, in_type2, rules[in_type2][1]) )

for source, sink, datatype, dataset in combinations:
    # Run all combinations of slow and 1way/2way
    test_full(host, source, sink, datatype, dataset, True, False)
    #test_full(host, source, sink, datatype, dataset, True, True)
    test_full(host, source, sink, datatype, dataset, False, False)
    #test_full(host, source, sink, datatype, dataset, False, True)

    # conduit.mappingDB.delete()

host.model.quit()
