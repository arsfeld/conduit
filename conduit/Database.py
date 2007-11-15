"""
stores.py
Copyright (C) Christian Hergert 2007 <christian.hergert@gmail.com>

stores.py is free software.

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
import logging
log = logging.getLogger("Database")

#for generic db
try:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    from pysqlite2 import dbapi2 as sqlite

#for threadsafe db
from threading import Thread
from Queue import Queue

#for lru decorator
from collections import deque

def lru_cache(maxsize):
    """
    Decorator applying a least-recently-used cache with the given maximum size.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    """
    if maxsize == 0:
        decorating_function = lambda x: x
    else:
        def decorating_function(f):
            cache = {}        # mapping of args to results
            queue = deque()        # order that keys have been accessed
            refcount = {}        # number of times each key is in the access queue
            def wrapper(*args):
                # localize variable access (ugly but fast)
                _cache=cache; _len=len; _refcount=refcount; _maxsize=maxsize
                queue_append=queue.append; queue_popleft = queue.popleft

                # get cache entry or compute if not found
                try:
                    result = _cache[args]
                    wrapper.hits += 1
                except KeyError:
                    result = _cache[args] = f(*args)
                    wrapper.misses += 1

                # record that this key was recently accessed
                queue_append(args)
                _refcount[args] = _refcount.get(args, 0) + 1

                # Purge least recently accessed cache contents
                while _len(_cache) > _maxsize:
                    k = queue_popleft()
                    _refcount[k] -= 1
                    if not _refcount[k]:
                        del _cache[k]
                        del _refcount[k]
        
                # Periodically compact the queue by duplicate keys
                if _len(queue) > _maxsize * 4:
                    for i in [None] * _len(queue):
                        k = queue_popleft()
                        if _refcount[k] == 1:
                            queue_append(k)
                        else:
                            _refcount[k] -= 1
                    assert len(queue) == len(cache) == len(refcount) == sum(refcount.itervalues())

                return result
            wrapper.__doc__ = f.__doc__
            wrapper.__name__ = f.__name__
            wrapper.hits = wrapper.misses = 0
            return wrapper

    return decorating_function
    
class GenericDB(gobject.GObject):

    __gsignals__ = {
        "row-inserted" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_INT]),         #row oid
        "row-modified" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_INT]),         #row oid
        "row-deleted" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_INT])          #row oid
        }
        
    DEBUG = True
        
    def __init__(self, filename=":memory:", **kwargs):
        gobject.GObject.__init__(self)
        #dictionary of field names, key is table name
        self.tables = {}
        self.filename = filename
        self.options = kwargs
        
        self._open()
        self._get_tables()

    def _open(self):
        #Open the DB and set options
        if self.options.get("detect_types",False):
            self.db = sqlite.connect(self.filename, detect_types=sqlite.PARSE_DECLTYPES)
        else:
            self.db = sqlite.connect(self.filename)
        self.db.isolation_level = self.options.get("isolation_level",None)
        if self.options.get("row_by_name",False) == True:
            self.db.row_factory = sqlite.Row
        self.cur = self.db.cursor()

    def _get_tables(self):
        #get the field names for all tables
        for name, in self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' and name != 'sqlite_sequence'"):
            self.tables[str(name)] = [row[1] for row in cur.execute("PRAGMA table_info('%s')" % name) if row[1] != 'oid']
            
    def _build_insert_sql(self, table, *values):
        assert(self.tables.has_key(table))
        assert(len(values) == len(self.get_fields(table)))
        sql = "INSERT INTO %s(oid" % table
        for f in self.get_fields(table):
            sql = sql + ", %s" % f
        sql = sql + ") VALUES ("
    
        #add None to values so that oid autoincrements
        values = (None,) + values        
        #add ? for each value (including oid), strip last ,
        sql = sql + ("?, "*len(values))[0:-2] + ")"
        return sql,values

    def _build_update_sql(self, table, oid, *values, **kwargs):
        assert(self.tables.has_key(table))
        if len(kwargs) > 0:
            values = kwargs.values()
            fields = kwargs.keys()
        else:
            fields = self.get_fields(table)

        assert( len(values) == len(fields) )
        sql = "UPDATE %s SET " % table
        for f in fields:
            sql = sql + "%s=?," % f
        #strip trailing ,
        sql = sql[0:-1] + " "
        sql = sql + "WHERE oid = %s" % oid
        return sql, values

    def _build_create_sql(self, table, fields, fieldtypes):
        #the default type is TEXT
        if len(fieldtypes) == 0:
            fieldtypes = ('TEXT',) * len(fields)
    
        sql = "CREATE TABLE %s (oid INTEGER PRIMARY KEY AUTOINCREMENT" % table
        for i in range(0,len(fields)):
            sql = sql + ", %s %s" % (fields[i],fieldtypes[i])
        sql = sql + ")"
        return sql
        
    def execute(self, sql, args=()):
        if GenericDB.DEBUG: log.debug(sql)
        self.cur.execute(sql, args)
        
    def select(self, sql, args=()):
        self.execute(sql, args)
        for raw in self.cur:
            yield raw

    def select_one(self, sql, args=()):
        for i in self.select(sql, args):
            return i

    def create(self, table, fields=(), fieldtypes=()):
        sql = self._build_create_sql(table, fields, fieldtypes)
        self.execute(sql)

        #save the field names
        self.tables[table] = fields

    def insert(self, table, values=()):
        sql,values = self._build_insert_sql(table, *values)
        self.execute(sql, values)
        self.emit("row-inserted",int(self.cur.lastrowid))
        return self.cur.lastrowid

    def update(self, table, oid, values=(), **kwargs):
        sql, values = self._build_update_sql(table, oid, *values, **kwargs)
        self.execute(sql, values)
        self.emit("row-modified", int(oid))

    def delete(self, table, oid):
        assert(self.tables.has_key(table))
        self.emit("row-deleted", int(oid))
        sql = "DELETE from %s where oid=?" % table
        self.execute(sql,(oid,))

    def save(self):
        self.db.commit()

    def close(self):
        self.cur.close()
        self.db.close()
        
    def debug(self, width=70, printoid=True):
        for table in self.tables:
            fields = self.get_fields(table)
            #Decide whether to print the oid or not
            if printoid:
                fields = ('oid',) + tuple(fields)
                fieldIndices = range(0, len(fields))
            else:
                fieldIndices = range(1, len(fields))

            MAX_WIDTH = width
            FIELD_MAX_WIDTH = MAX_WIDTH/len(fields)

            # Print a header.
            padding = '-'*MAX_WIDTH
            print padding + "\nTABLE: %s\n" % table + padding

            for field in fields:
                print field.ljust(FIELD_MAX_WIDTH) ,
            print "\n" + padding

            # For each row, print the value of each field left-justified within
            # the maximum possible width of that field.
            for row in self.select("SELECT * from %s" % table):
                for fieldIndex in fieldIndices:
                    fieldValue = str(row[fieldIndex])
                    print fieldValue.ljust(FIELD_MAX_WIDTH) ,

                print

    def get_fields(self, table):
        """
        Returns the number of fields in the table EXCLUDING oid
        """
        assert(self.tables.has_key(table))
        return self.tables[table]
        
    def get_tables(self):
        return self.tables.keys()

class ThreadSafeGenericDB(Thread, GenericDB):
    #Adapted from
    #http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/526618
    def __init__(self, filename=":memory:", **kwargs):
        GenericDB.__init__(self,filename,**kwargs)
        Thread.__init__(self)
        self.reqs=Queue()
        self.stopped = False
        self.start()
        
    def _open(self):
        #open the db in the thread where it is used
        pass
        
    def _get_tables(self):
        db = sqlite.connect(self.filename)
        cur = db.cursor()
        #get the field names for all tables
        for name, in cur.execute("SELECT name FROM sqlite_master WHERE type='table' and name != 'sqlite_sequence'"):
            self.tables[str(name)] = [row[1] for row in cur.execute("PRAGMA table_info('%s')" % name) if row[1] != 'oid']
            
    def run(self):
        GenericDB._open(self)
        while not self.stopped:
            req, args, res, operation = self.reqs.get()
            if req=='--stop--': 
                self.stopped = True
            elif req=='--save--': 
                self.db.commit()
            else:
                self.cur.execute(req, args)

                #res is used to return a result to the caller
                #in a blocking way
                if res:
                    if operation == "SELECT":
                        for rec in self.cur:
                            res.put(rec)
                        res.put('--no more--')
                    elif operation == "INSERT":
                        res.put(self.cur.lastrowid)
                    else:
                        assert(False)

        self.cur.close()
        self.db.close()

    def execute(self, req, args=(), res=None, operation=""):
        if GenericDB.DEBUG: log.debug(req)
        if not self.stopped:
            self.reqs.put((req, args, res, operation))

    def select(self, req, args=()):
        res=Queue()
        self.execute(req, args, res, "SELECT")
        while not self.stopped:
            rec=res.get()
            if rec=='--no more--': break
            yield rec

    def close(self):
        self.execute('--stop--')

    def save(self):
        self.execute('--save--')

    def insert(self, table, values=()):
        sql,values = self._build_insert_sql(table, *values)
        res=Queue()
        self.execute(sql, values, res, "INSERT")
        while not self.stopped:
            newId = res.get()
            self.emit("row-inserted",int(newId))
            return newId

