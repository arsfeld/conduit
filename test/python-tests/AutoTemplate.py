import sys, threading, thread, inspect, datetime

#common sets up the conduit environment
from common import *

# we are going to wrap some debugging code around our internals..
import conduit.Synchronization as Sync
import conduit.Exceptions as Exceptions

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
    for i in range(0, len(dataset)):
        obj = convert(host, datatype, dp.in_type, dataset[i])
        dp.module.put(obj, False)

    dp.module.refresh()
    ok("Dataset loaded into source", dp.module.get_num_items() == len(dataset)) 

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
    try:
        test_full(host, source, sink, datatype, dataset, True, False)
        # test_full(host, source, sink, datatype, dataset, True, True)
        test_full(host, source, sink, datatype, dataset, False, False)
        # test_full(host, source, sink, datatype, dataset, False, True)

    except (KeyboardInterrupt, SystemExit):
        pass

    except:
        sys.excepthook(*sys.exc_info())

    host.model.quit()

#try:
#    if os.environ["STRESS_TEST"] != "YES":
#        sys.exit()
#except:
#    sys.exit()

# Catch exceptions better
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

# Intialise sync management framework
host = SimpleSyncTest()
host.set_two_way_policy({
                "conflict"  :   "replace",
                "deleted"   :   "replace"}
                )

