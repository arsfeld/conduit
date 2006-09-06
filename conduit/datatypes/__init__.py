"""
Exposes the DataTypes for public use

It is expected that DataProviders (written by the user, or included within
Conduit) may require the use of DataTypes other than their own in their
implementation. For example all email programs should share the same common
mail datatype. For this reason DataTypes, not DataProviders are exported
"""

import Feed
import File
import Note
import Text
import Email
import DataType

__all__ = ["Feed", "File", "Note", "Text", "Email", "DataType"]

#Constants used for comparison
COMPARISON_EQUAL = 0
COMPARISON_NEWER = 1
COMPARISON_OLDER = 2
COMPARISON_UNKNOWN = 3

    
