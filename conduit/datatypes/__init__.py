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
COMPARISON_UNKNOWN = 3

import datetime
import logging
log = logging.getLogger("datatypes.Rid")

class Rid(object):

    def __init__(self, uid=None, mtime=None, hash=""):
        """
        @param uid: str or None
        @param mtime: datetime or None
        @param hash: str
        """
        self.uid = uid
        self.mtime = mtime
        self.hash = str(hash)

        assert (type(uid) == str or type(uid) == unicode or uid == None), "UID must be unicode,string or None not %s" % type(uid)
        assert (type(mtime) == datetime.datetime or mtime == None), "mtime must be datatime or None not %s" % type(datetime)

    def __eq__(self, other):
        if other == None:
            return False
        #log.debug("EQ: UID:%s mtime:%s hash:%s" % (self.uid != other.uid, self.mtime != other.mtime, self.hash != other.hash))
        #log.debug("EQ Types: UID:%sv%s mtime:%sv%s hash:%sv%s" % (type(self.uid),type(other.uid),type(self.mtime),type(other.mtime),type(self.hash),type(other.hash)))
        return self.uid == other.uid and self.mtime == other.mtime and self.hash == other.hash
        
    def __ne__(self, other):
        if other == None:
            return True
        #log.debug("NE: UID:%s mtime:%s hash:%s" % (self.uid != other.uid, self.mtime != other.mtime, self.hash != other.hash))
        #log.debug("NE Types: UID:%sv%s mtime:%sv%s hash:%sv%s" % (type(self.uid),type(other.uid),type(self.mtime),type(other.mtime),type(self.hash),type(other.hash)))
        return self.uid != other.uid or self.mtime != other.mtime or self.hash != other.hash

    def __hash__(self):
        return hash( (self.uid, self.mtime, self.hash) )
        
    def __str__(self):
        return "UID:%s mtime:%s hash:%s" % (self.uid, self.mtime, self.hash)

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

