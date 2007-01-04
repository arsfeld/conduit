"""
Shared API for comparing the previous state of a dp to the current 
state. Returns only changes to core synch mechanism.

This class is a proxy for the TwoWay dataprovider. It filter's incoming
and outgoing objects so we can detect changes rather than trying to sync 
everything

Copyright: John Stowers, 2006
License: GPLv2
"""

import os, md5, cPickle
import conduit.DataProvider as DataProvider
import conduit.datatypes.DataType as DataType

#fixme - conduit will try and create a widget for any dataprovider...
#fixme - for CHANGE_DELETED, new DataType is created.. but wrong 
#         type is passed to __init__ (hardcoded to "note")

class DeltaProvider(DataProvider.TwoWay):
    _name_ = ""
    _description_ = ""

    def __init__(self, dp):
        DataProvider.TwoWay.__init__(self)

        self.provider = dp
        self._delta_file = "hashtable.db"

        self.db = {}
        if os.path.exists(self._delta_file):
            f = open(self._delta_file)
            self.db = cPickle.load(f)

        self.accessed = {}

    def refresh(self):
        """ Call refresh on target dp and filter the output so we only return
            changes to sync code
        """
        DataProvider.TwoWay.refresh(self)

        self.changes = []

        self.provider.refresh()
        for i in range(0, self.provider.get_num_items()):
            obj = self.provider.get(i)
            key = obj.get_UID()

            self.accessed[key] = key

            if not key in self.db:
                obj.change_type = DataType.CHANGE_ADDED
            elif self.db[key]['hash'] != obj.get_hash():
                obj.change_type = DataType.CHANGE_MODIFIED

            # if the change_type has been set, add it to list of things to return to Conduit
            if obj.change_type != DataType.CHANGE_UNMODIFIED:
                self.changes.append(obj)

        # these are the UID's that are no longer in the dp - they must have been deleted!
        for r in [r for r in self.db if r not in self.accessed]:
            obj = DataType.DataType("note")
            obj.set_UID(self.db[r]['LUID'])
            obj.change_type = DataType.CHANGE_DELETED
            self.changes.append(obj)

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.changes)

    def get(self, index):
        DataProvider.TwoWay.get(self,index)
        return self.changes[index]

    def put(self, change, overwrite):
        DataProvider.TwoWay.put(self, change, overwrite)

        # get UID of change...
        current_uid = change.get_UID()

        # actually "commit" the change to the real dp
        self.provider.put(change, overwrite)

        # record the hash of the object..
        self.db[change.get_UID()]['hash'] = change.get_hash()

        # has UID changed? delete old UID from self.db
        if current_uid != change.get_UID():
            self._delete(self, current_uid)

    def finish(self):
        for c in self.changes:
            if c.change_type == DataType.CHANGE_DELETED:
                self._delete(c.get_UID())
            else:
                self.db[c.get_UID()] = {}
                self.db[c.get_UID()]['hash'] = c.get_hash()
                self.db[c.get_UID()]['LUID'] = c.get_UID()

        f = open(self._delta_file, 'w+')
        f.write(cPickle.dumps(self.db))
        f.close()
        return

    def _delete(self, UID):
        """ Remove an item from self.db """
        del self.db[UID]

