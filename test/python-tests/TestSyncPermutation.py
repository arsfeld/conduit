import sys, threading, thread, inspect, datetime

#common sets up the conduit environment
from common import *

# we are going to wrap some debugging code around our internals..
import conduit.Synchronization as Sync

# import any datatypes that are needed
import conduit.datatypes.File as File
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Note as Note

# import any dp's that we'll need to wrap
from conduit.dataproviders import iPodModule

try:
    if os.environ["STRESS_TEST"] != "YES":
        sys.exit()
except:
    sys.exit()

def catch(old_func):
    def func(*args, **kwargs):
        try:
            return old_func(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            sys.excepthook(*sys.exc_info())
            thread.interrupt_main()

    func.__doc__ = old_func.__doc__
    return func

threading.Thread.run = catch(threading.Thread.run)
Sync.SyncWorker.run = catch(Sync.SyncWorker.run)

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
    ok("Got %d sample contacts" % len(objs), len(objs) > 0)
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
    ok("Got %d sample events" % len(objs), len(objs) > 0)
    return objs

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

def objset_files():
    """
    Return a sample of file objects
    """
    objs = [File.File(f) for f in get_files_from_data_dir("*")]
    ok("Got %d sample contacts" % len(objs), len(objs) > 0)
    return objs

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

def prep_ipod_notes(host):
    source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod notes " + Utils.random_string())
    if not os.path.exists(source_folder):
        os.mkdir(source_folder)
    return host.wrap_dataprovider( iPodModule.IPodNoteTwoWay(source_folder, "") )

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

#def prep_tomboy(host):
#    dp = host.get_dataprovider("TomboyTwoWay")
#    return dp

def prep_evo_contacts(host):
    dp = host.get_dataprovider("EvoContactTwoWay")
    opts = dict(dp.module._addressBooks)
    dp.module.set_configuration( { "sourceURI": opts["conduit-test"], } )
    return dp

#def prep_evo_calendar(host):
#    dp = host.get_dataprovider("EvoCalendarTwoWay")
#    opts = dict(dp.module._calendarURIs)
#    dp.module.set_configuration( { "sourceURI": opts["conduit-test"], } )
#    return dp

#def prep_evo_memo(host):
#    dp = host.get_dataprovider("EvoMemoTwoWay")
#    opts = dict(dp.module._memoSources)
#    dp.module.set_configuration( { "sourceURI": opts["conduit-test"], } )
#    return dp

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

def test_sync(host, should_change=True):
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

    if should_change:
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
    ok("Testing MODIFY Case (Prepare)", True)
    dp.module.refresh()
    uids = dp.module.get_all()
    for uid in uids:
        obj = dp.module.get(uid)
        obj.set_mtime(datetime.datetime.now())
        dp.module.put(obj, True, uid)
    ok("Testing MODIFY Case (Sync Runs)", True)
    test_sync(host, False)
    ok("Testing MODIFY Case (Complete)", True)

def test_delete_data(host, dp):
    a = host.get_source_count()
    b = host.get_sink_count()
    ok("Testing DELETE Case (Prepare)", a==b)

    dp.module.refresh()
    uids = dp.module.get_all()
    for uid in uids:
        obj = dp.module.get(uid)
        obj.set_mtime(datetime.datetime.now())
        dp.module.delete(uid)

    dp.module.refresh()
    ok("Testing DELETE Case (Prepared)", len(dp.module.get_all()) == 0)

    test_sync(host)
    # ok("Testing DELETE Case (Complete)", a == 0 and b == 0)

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

    # Fresh data (source end), and try modifying data on both sides
    test_clear(host)
    test_add_data(host, host.source, datatype, dataset)
    test_modify_data(host, host.source)
    test_modify_data(host, host.sink)

    # Fresh data (source end), delete on source + sync
    test_clear(host)
    test_add_data(host, host.source, datatype, dataset)
    test_delete_data(host, host.source)

    if twoway:
        # Fresh data (source end), delete on sink + sync
        test_clear(host)
        test_add_data(host, host.source, datatype, dataset)
        test_delete_data(host, host.sink)

    # Same tests again, but inject at the sink.
    # Only makes sense in the twoway case
    if twoway:
        # Fresh data (source end), and try modifying data on both sides
        test_clear(host)
        test_add_data(host, host.sink, datatype, dataset)
        test_modify_data(host, host.source)
        test_modify_data(host, host.sink)

        # Fresh data (source end), delete on source + sync
        test_clear(host)
        test_add_data(host, host.sink, datatype, dataset)
        test_delete_data(host, host.source)

        # Fresh data (source end), delete on sink + sync
        test_clear(host)
        test_add_data(host, host.sink, datatype, dataset)
        test_delete_data(host, host.sink)

    test_clear(host)

def test_full_set(host, source, sink, datatype, dataset):
    """
    Call test_full 4 times to test 1way + 2way (w and w/out slow-sync)
    """
    test_full(host, source, sink, datatype, dataset, True, False)
    # test_full(host, source, sink, datatype, dataset, True, True)
    test_full(host, source, sink, datatype, dataset, False, False)
    # test_full(host, source, sink, datatype, dataset, False, True)

try:
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
        "note":     (5, objset_notes),
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

    count = 0
    
    for source, sink, datatype, dataset in combinations:
        test_full_set(host, source, sink, datatype, dataset)
        
        if datatype in ("contact", "note"):
            newsource = host.networked_dataprovider(source)
            test_full_set(host, newsource, sink, datatype, dataset)
            
            newsink = host.networked_dataprovider(sink)
            test_full_set(host, source, newsink, datatype, dataset)

            test_full_set(host, newsource, newsink, datatype, dataset)

        #conduit.mappingDB.delete()
        count += 1

    ok("%d combinations of dataprovider tested" % count, count > 0)

except (KeyboardInterrupt, SystemExit):
    pass

except:
    sys.excepthook(*sys.exc_info())

host.model.quit()
