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

def compare_mtimes_and_hashes(data1, data2):
    """
    Compares data based upon its mtime and hashes only
    """
    mtime1 = data1.get_mtime()
    mtime2 = data2.get_mtime()
    hash1 = data1.get_hash()
    hash2 = data2.get_hash()
