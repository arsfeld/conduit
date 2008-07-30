"""
GtkListStore wrapping around Generic DB Abstraction layer, including a lru
cache to speed up operation.
Copyright (C) John Stowers 2007 <john.stowers@gmail.com>

Based on http://vwdude.com/dropbox/pystore/
Copyright (C) Christian Hergert 2007 <christian.hergert@gmail.com>

You may redistribute it and/or modify it under the terms of the
GNU General Public License, as published by the Free Software
Foundation; either version 2 of the License, or (at your option)
any later version.
 
main.c is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License
along with main.c.  If not, write to:
 The Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor
 Boston, MA  02110-1301, USA.
"""
import gobject
import gtk
import logging
log = logging.getLogger("gtkui.Database")

import conduit.Database as DB
import conduit.utils as Utils

class GenericDBListStore(gtk.GenericTreeModel):
    """
    gtk.TreeModel implementation that saves and stores data directly
    to and from a sqlite database. A simple LRU cache is included to
    lower the number of required SQL queries.
    """

    OID_CACHE = True

    def __init__(self, table, genericDB):
        """
        Creates a new GenericDBListStore.
        
        Parameters:
            filename -- the filename of the sqlite database.
            table -- the name of the table to manage.
        """
        gtk.GenericTreeModel.__init__(self)
        genericDB.connect("row-inserted",self._on_inserted)
        genericDB.connect("row-deleted",self._on_deleted)
        genericDB.connect("row-modified",self._on_modified)
        
        self.table = table
        self.db = genericDB
        self.oidcache = []
        self.columns = self._get_columns()
        
    def _on_inserted(self, db, oid):
        self.oidcache = []
        offset = self._get_offset(oid)
        rowref = self.get_iter(offset)
        path = self.get_path(rowref)
        self.row_inserted(path, rowref)
                
    def _on_modified(self, db, oid):
        self.oidcache = []
        offset = self._get_offset(oid)
        rowref = self.get_iter(offset)
        path = self.get_path(rowref)
        self.row_changed(path, rowref)
        
    def _on_deleted(self, db, oid):
        self.oidcache = []
        offset = self._get_offset(oid)
        rowref = self.get_iter(offset)
        path = self.get_path(rowref)
        self.row_deleted(path)

    def _get_n_rows(self):
        """
        Returns the number of rows found in our loaded table inside
        the sqlite database.
        """
        (rows,) = self.db.select_one("SELECT COUNT(oid) FROM %s" % self.table)
        return rows
    
    def _get_columns(self):
        """
        Returns the number of columns found in our sqlite table.
        """
        return ('oid',) + tuple(self.db.get_fields(self.table))
    
    @DB.lru_cache(0)
    def _get_oid(self, offset):
        """
        Returns the oid of the row at offset.
        
        Parameters:
            offset -- the rows offset from 0.
        """
        (oid,) = self.db.select_one("SELECT oid FROM %s LIMIT 1 OFFSET %d" % (self.table, offset))
        return oid
    
    @DB.lru_cache(0)
    def _get_value(self, oid, index):
        """
        Returns the value for a column in the table with a row id
        of oid.
        
        Parameters:
            oid -- the rows internal oid.
            column -- the column index.
        """
        (value,) = self.db.select_one("SELECT %s FROM %s WHERE oid = %d" % (self.columns[index], self.table, oid))
        return value
    
    @DB.lru_cache(0)
    def _get_next_oid(self, oid):
        """
        Returns the next oid after passed oid.
        
        Note: for some reason unknown to me, gtk.TreeView or
        perhaps the GenericTreeModel finds it neccessary to
        iterate through every iter from the root node through
        n_children. Because of this, we will fetch row ids in
        sets of 1024 and cache them to speed things up.
        
        Parameters:
            oid -- the current oid.
        """
        #first call is when oid=None
        if not oid:
            oid = -1
            
        if GenericDBListStore.OID_CACHE:
            try:
                index = self.oidcache.index(oid)
                return self.oidcache[index+1]
            except (ValueError, IndexError):
                sql = "SELECT oid FROM %s WHERE oid >= %d LIMIT 1024" % (self.table, oid)
                oids = [oid for (oid,) in self.db.select(sql)]
                self.oidcache.extend(oids)
                self.oidcache = Utils.unique_list(self.oidcache)
            #if we can only get one result, we must be the last oid
            if len(oids) > 1:
                oid = oids[1] 
            else:
                oid = None        
        else:
            try:
                (oid,) = self.db.select_one("SELECT oid FROM %s WHERE oid > %d LIMIT 1" % (self.table, oid))
            except TypeError:
                oid = None

        return oid
    
    def _get_offset(self, oid):
        """
        Returns the offset of oid in the sqlite table.
        
        Parameters:
            oid -- the oid of the row to check
        """
        (offset,) = self.db.select_one("SELECT COUNT(oid) FROM %s WHERE oid < %d" % (self.table, oid))
        return offset
    
    def on_get_flags(self):
        """
        Returns the gtk.TreeModelFlags for the gtk.TreeModel
        implementation. The gtk.TreeIter data is derived from
        the database oids for records and therefore is persistant
        across row deletion and inserts.
        """
        return gtk.TREE_MODEL_LIST_ONLY | gtk.TREE_MODEL_ITERS_PERSIST
    
    def on_get_n_columns(self):
        """
        Returns the number of columns found in the table metadata.
        """
        return len(self.columns)
    
    def on_get_column_type(self, index):
        """
        All columns in sqlite are accessed via (char*). Therefore,
        all of our column types will pass that right along and
        allow the consumers to typecast as needed.
        """
        return gobject.TYPE_STRING
    
    def on_get_iter(self, path):
        """
        Traslates a gtk.TreePath to a gtk.TreeIter. This is done by
        finding the oid for the row in the database at the same
        offset as the path.
        """
        if len(path) > 1:
            return None #We are a list not a tree
        try:
            return self._get_oid(path[0])
        except TypeError:
            return None #DB is empty
    
    def on_get_path(self, rowref):
        """
        Returns the rowrefs offset in the table which is used to
        generate the gtk.TreePath.
        """
        return self._get_offset(rowref)
    
    def on_get_value(self, rowref, column):
        """
        Returns the data for a rowref at the givin column.
        
        Parameters:
            rowref -- the rowref passed back in the on_get_iter
                         method.
            column -- the integer offset of the column desired.
        """
        if column > len(self.columns):
            return None
        if column == 0:
            return rowref
        return self._get_value(rowref, column)
    
    def on_iter_next(self, rowref):
        """
        Returns the next oid found in the sqlite table.
        
        Parameters:
            rowref -- the oid of the current iter.
        """
        return self._get_next_oid(rowref)
    
    def on_iter_children(self, rowref):
        """
        Retruns children for a given rowref. This will always be
        None unless the rowref is None, which is our root node.
        
        Parameters:
            rowref -- the oid of the desired row.
        """
        if rowref:
            return None
        return self._get_next_oid(-1)
    
    def on_iter_has_child(self, rowref):
        """
        Always returns False as List based TreeModels do not have
        children.
        """
        return False
    
    def on_iter_n_children(self, rowref):
        """
        Returns the number of children a row has. Since only the
        root node may have children, we return 0 unless the request
        is made for the count of all rows. Requesting the row count
        is done by passing None as the rowref.
        """
        if rowref:
            return 0
        return self._get_n_rows()
    
    def on_iter_nth_child(self, rowref, n):
        """
        Returns the oid of the nth child from rowref. This will
        only return a value if rowref is None, which is the
        root node.
        
        Parameters:
            rowref -- the oid of the row.
            n -- the row offset to retrieve.
        """
        if rowref:
            return None
        return self._get_oid(n)
    
    def on_iter_parent(self, child):
        """
        Always returns None as lists do not have parent nodes.
        """
        return None
