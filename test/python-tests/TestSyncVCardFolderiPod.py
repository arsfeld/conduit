#common sets up the conduit environment
from common import *

# import any datatypes that are needed
import conduit.datatypes.File as File
import conduit.datatypes.Contact as Contact

# import any dp's that we'll need to wrap
from conduit.dataproviders import iPodModule


class IPod_VCard(SimpleSyncTest):
    def get_source(self):
        self.source_folder = os.path.join(os.environ['TEST_DIRECTORY'], "ipod-contacts")
        if not os.path.exists(self.source_folder):
            os.mkdir(self.source_folder)

        return self.wrap_dataprovider( iPodModule.IPodContactsTwoWay(self.source_folder, "") )

    def get_sink(self):
        self.sink_folder = os.path.join(os.environ['TEST_DIRECTORY'], "folder-contacts")
        if not os.path.exists(self.sink_folder):
            os.mkdir(self.sink_folder)

        dp = self.get_dataprovider("FolderTwoWay")
        dp.module.folder = self.sink_folder
        return dp

def test_add_sync_sync(obj):
    """
    If the source has 3 items and the sink has 0 then after the first sync
    both sides should have 3.

    Syncing straight away for a 2nd time should give no change
    """
    a, b = test.sync()
    ok("Sync with no items", a == 0 and b == 0)

    # copy in some dummy data...
    vcards = get_files_from_data_dir("*.vcard")
    for i in range(0, len(vcards)):
        c = Contact.Contact(vcards[i])
        c.set_from_vcard_string( read_data_file(vcards[i]) )
        test.source.module.put(c, True, str(i))

    # get the counts before we start
    a1 = test.get_source_count()
    b1 = test.get_sink_count()

    # after the first sync the counts should be the same on both sides
    a2, b2 = test.sync()
    ok("Sync worked (source had %s, source has %s, sink had %s, sink has %s)" % (a1, a2, b1, b2), a1==a2 and a2==b2)

    # after the third sync nothing should have changed
    a3, b3 = test.sync()
    ok("Sync worked (source had %s, source has %s, sink had %s, sink has %s)" % (a2, a3, b2, b3), a2==a3 and a3==b3)

test = IPod_VCard()
test.set_two_way_sync(True)
test_add_sync_sync(test)

# test = IPod_VCard()
# test.set_two_way_sync(True)
# test.set_slow_sync(True)
# test_add_sync_sync(test)

