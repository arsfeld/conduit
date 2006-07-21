"""
Exposes the DataTypes for public use

It is expected that DataProviders (written by the user, or included within
Conduit) may require the use of DataTypes other than their own in their
implementation. For example all email programs should share the same common
mail datatype. For this reason DataTypes, not DataProviders are exported
"""


import File
import Note
import Text
import Email
import DataType

__all__ = ["File", "Note", "Text", "Email", "DataType"]

#Constants used for comparison
EQUAL = 0
NEWER = 1
OLDER = 2
ERROR = 3
