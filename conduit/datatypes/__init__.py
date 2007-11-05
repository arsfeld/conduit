"""
Exposes the DataTypes for public use

It is expected that DataProviders (written by the user, or included within
Conduit) may require the use of DataTypes other than their own in their
implementation. For example all email programs should share the same common
mail datatype. For this reason DataTypes, not DataProviders are exported
"""
#Constants used for comparison
COMPARISON_EQUAL = 0
COMPARISON_NEWER = 1
COMPARISON_OLDER = 2
COMPARISON_UNEQUAL = 3
COMPARISON_UNKNOWN = 4

class Rid(object):

    def __init__(self, uid=None, mtime=None, hash=None):
        self.uid = uid
        self.mtime = mtime
        self.hash = hash

    def __equ__(self, b):
        return self.uid == b.uid and self.mtime == b.mtime and self.hash == b.hash

    def get_UID(self):
        return self.uid

    def get_mtime(self):
        return self.mtime

    def get_hash(self):
        return self.hash

    def __getstate__(self):
        """
        Store the Rid state in a dict for pickling
        """
        data = {}
        data['uid'] = self.uid
        data['mtime'] = self.mtime
        data['hash'] = self.hash
        return data

    def __setstate__(self, data):
        """
        Restore Rid state from dict (after unpickling)
        """
        self.uid = data['uid']
        self.mtime = data['mtime']
        self.hash = data['hash']


def compare_mtimes_and_hashes(data1, data2):
    """
    Compares data based upon its mtime and hashes only
    """
    mtime1 = data1.get_mtime()
    mtime2 = data2.get_mtime()
    hash1 = data1.get_hash()
    hash2 = data2.get_hash()
