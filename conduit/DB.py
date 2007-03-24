import os, os.path
import cPickle
import bisect

import conduit
import conduit.Utils as Utils
from conduit import log,logd,logw

class MappingDB:
    """
    Manages mappings of LUID <--> LUID on a per dataprovider basis.
    Table with 5 fields -
        1. Source Wrapper UID
        2. Source Data LUID
        3. Sink Wrapper UID
        4. Sink Data LUID
        5. Modification Time

    This class is a mapping around a simple python dict based DB. This wrapper
    will make it easier to swap out database layers at a later date. 
    @todo: Add thread locks around all DB calls
    """
    def __init__(self):
        self._db = None

    def get_mappings_for_dataproviders(self, sourceUID, sinkUID):
        """
        Gets all the data mappings for the dataprovider pair
        sourceUID <--> sinkUID
        """
        return [i for i in self._db if i["sourceUID"] == sourceUID and i["sinkUID"] == sinkUID]
        
    def open_db(self, filename):
        """
        Opens the mapping DB at the location @ filename
        """
        self._db = SimpleDb(os.path.abspath(filename))
        self._db.create("sourceUID","sourceDataLUID", "sinkUID", "sinkDataLUID","mtime", mode="open")
        #We access the DB via all fields so all need indices
        self._db.create_index(*self._db.fields)

    def save_mapping(self, sourceUID, sourceDataLUID, sinkUID, sinkDataLUID, mtime):
        """
        Saves a mapping between the dataproviders with sourceUID and sinkUID
        The mapping says that within that syncronization pair the two data
        items sourceeDataLUID and sinkDataLUID are synchronized
        """
        if None in [sourceUID, sourceDataLUID, sinkUID, sinkDataLUID]:
            logw("Could not save mapping")
            return

        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                if i["sinkDataLUID"] == sinkDataLUID and i["mtime"] == mtime:
                    logd("Skipping mapping: %s --> %s" % (sourceDataLUID,sinkDataLUID))
                    return
                else:
                    logd("Updating mapping: %s --> %s" % (sourceDataLUID,sinkDataLUID))
                    self._db.update(
                        i,
                        sourceDataLUID=sourceDataLUID,
                        sinkDataLUID=sinkDataLUID,
                        mtime=mtime
                        )
                    return


        logd("Saving new mapping: %s --> %s" % (sourceDataLUID,sinkDataLUID))
        self._db.insert(
                    sourceUID=sourceUID,
                    sourceDataLUID=sourceDataLUID,
                    sinkUID=sinkUID,
                    sinkDataLUID=sinkDataLUID,
                    mtime=mtime
                    )

    def get_mapping(self, sourceUID, sourceDataLUID, sinkUID):
        """
        For a given source and sink pair, get the mapping data for
        the sourceDataLUID. This includes the matching sinkDataLUID
        and mtime.

        @returns: sinkDataLUID, mtime
        """
        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                return i["sinkDataLUID"], i["mtime"]

        return None, None

    def delete_mapping(self, sourceUID, sourceDataLUID, sinkUID):
        """
        Deletes mapping between the dataproviders sourceUID and sinkUID
        that involve sourceDataLUID

        @returns: The number of mappings deleted
        """
        if dataLUID == None:
            logw("Could not delete NULL mapping %s <--> %s" % (sourceUID, sinkUID))
            return 0

        delete = []
        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                delete.append(i)

        num = self._db.delete(delete)
        logd("%s mappings deleted for mapping %s <--> %s" % (num, sourceUID, sinkUID))
        return num

    def save(self):
        logd("Saving mapping DB to %s" % self._db.name)
        self._db.commit()

    def debug(self):
        s = "Contents of MappingDB: %s\n" % self._db.name
        sources = [i["sourceUID"] for i in self._db]
        sources = Utils.distinct_list(sources)
        for sourceUID in sources:
            s += "\t%s:\n" % sourceUID
            #all matching sinkUIDs for sourceUID
            sinks = [i["sinkUID"] for i in self._db if i["sourceUID"] == sourceUID]
            sinks = Utils.distinct_list(sinks)
            for sinkUID in sinks:
                s += "\t\t%s --> %s\n" % (sourceUID, sinkUID)
                #get relationships
                rels = self.get_mappings_for_dataproviders(sourceUID, sinkUID)
                for r in rels:
                    s += "\t\t\t%s --> %s\n" % (r["sourceDataLUID"], r["sinkDataLUID"])
        return s
      
        
class SimpleDb:
    """
    In-memory database management, with selection by list comprehension 
    or generator expression

    Fields are untyped : they can store anything that can be pickled.
    Selected records are returned as dictionaries. Each record is 
    identified by a unique id

    See: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496770
    """
    def __init__(self,basename):
        self.name = basename

    def create(self,*fields,**kw):
        """Create a new base with specified field names
        A keyword argument mode can be specified ; it is used if a file
        with the base name already exists
        - if mode = 'open' : open the existing base, ignore the fields
        - if mode = 'override' : erase the existing base and create a
        new one with the specified fields"""
        self.mode = mode = kw.get("mode",None)
        if os.path.exists(self.name):
            if not os.path.isfile(self.name):
                raise IOError,"%s exists and is not a file" %self.name
            elif mode is None:
                raise IOError,"Base %s already exists" %self.name
            elif mode == "open":
                return self.open()
            elif mode == "override":
                os.remove(self.name)
        self.fields = list(fields)
        self.records = {}
        self.next_id = 0
        self.indices = {}
        self.commit()
        return self

    def create_index(self,*fields):
        """Create an index on the specified field names
        
        An index on a field is a mapping between the values taken by the field
        and the sorted list of the ids of the records whose field is equal to 
        this value
        
        For each indexed field, an attribute of self is created, an instance 
        of the class Index (see above). Its name it the field name, with the
        prefix _ to avoid name conflicts
        """
        for f in fields:
            if not f in self.fields:
                raise NameError,"%s is not a field name" %f
            # initialize the indices
            if self.mode == "open" and f in self.indices:
                continue
            self.indices[f] = {}
            for _id,record in self.records.iteritems():
                # use bisect to quickly insert the id in the list
                bisect.insort(self.indices[f].setdefault(record[f],[]),
                    _id)
            # create a new attribute of self, used to find the records
            # by this index
            setattr(self,'_'+f,_PyDbIndex(self,f))
        self.commit()

    def open(self):
        """Open an existing database and load its content into memory"""
        _in = open(self.name,'rb')
        self.fields = cPickle.load(_in)
        self.next_id = cPickle.load(_in)
        self.records = cPickle.load(_in)
        self.indices = cPickle.load(_in)
        for f in self.indices.keys():
            setattr(self,'_'+f,_PyDbIndex(self,f))
        _in.close()
        return self

    def commit(self):
        """Write the database to a file"""
        out = open(self.name,'wb')
        cPickle.dump(self.fields,out)
        cPickle.dump(self.next_id,out)
        cPickle.dump(self.records,out)
        cPickle.dump(self.indices,out)
        out.close()

    def insert(self,*args,**kw):
        """Insert a record in the database
        Parameters can be positional or keyword arguments. If positional
        they must be in the same order as in the create() method
        If some of the fields are missing the value is set to None
        Returns the record identifier
        """
        if args:
            kw = dict((f,arg) for f,arg in zip(self.fields,args))
        # initialize all fields to None
        record = dict((f,None) for f in self.fields)
        # set keys and values
        for (k,v) in kw.iteritems():
            record[k]=v
        # add the key __id__ : record identifier
        record['__id__'] = self.next_id
        # create an entry in the dictionary self.records, indexed by __id__
        self.records[self.next_id] = record
        # update index
        for ix in self.indices.keys():
            bisect.insort(self.indices[ix].setdefault(record[ix],[]),
                self.next_id)
        # increment the next __id__ to attribute
        self.next_id += 1
        return record['__id__']

    def delete(self,removed):
        """Remove a single record, or the records in an iterable
        Before starting deletion, test if all records are in the base
        and don't have twice the same __id__
        Return the number of deleted items
        """
        if isinstance(removed,dict):
            # remove a single record
            removed = [removed]
        else:
            # convert iterable into a list (to be able to sort it)
            removed = [ r for r in removed ]
        if not removed:
            return 0
        _ids = [ r['__id__'] for r in removed ]
        _ids.sort()
        keys = set(self.records.keys())
        # check if the records are in the base
        if not set(_ids).issubset(keys):
            missing = list(set(_ids).difference(keys))
            raise IndexError,'Delete aborted. Records with these ids' \
                ' not found in the base : %s' %str(missing)
        # raise exception if duplicate ids
        for i in range(len(_ids)-1):
            if _ids[i] == _ids[i+1]:
                raise IndexError,"Delete aborted. Duplicate id : %s" %_ids[i]
        deleted = len(removed)
        while removed:
            r = removed.pop()
            _id = r['__id__']
            # remove id from indices
            for indx in self.indices.keys():
                pos = bisect.bisect(self.indices[indx][r[indx]],_id)-1
                del self.indices[indx][r[indx]][pos]
                if not self.indices[indx][r[indx]]:
                    del self.indices[indx][r[indx]]
            # remove record from self.records
            del self.records[_id]
        return deleted

    def update(self,record,**kw):
        """Update the record with new keys and values and update indices"""
        # update indices
        _id = record["__id__"]
        for indx in self.indices.keys():
            if indx in kw.keys():
                if record[indx] == kw[indx]:
                    continue
                # remove id for the old value
                old_pos = bisect.bisect(self.indices[indx][record[indx]],_id)-1
                del self.indices[indx][record[indx]][old_pos]
                if not self.indices[indx][record[indx]]:
                    del self.indices[indx][record[indx]]
                # insert new value
                bisect.insort(self.indices[indx].setdefault(kw[indx],[]),_id)
        # update record values
        record.update(kw)

    def add_field(self,field,default=None):
        if field in self.fields:
            raise ValueError,"Field %s already defined" %field
        for r in self:
            r[field] = default
        self.fields.append(field)
        self.commit()
    
    def drop_field(self,field):
        self.fields.remove(field)
        for r in self:
            del r[field]
        if field in self.indices:
            del self.indices[field]
        self.commit()
    
    def __getitem__(self,record_id):
        """Direct access by record id"""
        return self.records[record_id]
    
    def __len__(self):
        return len(self.records)

    def __delitem__(self,record_id):
        """Delete by record id"""
        self.delete(self[record_id])
        
    def __iter__(self):
        """Iteration on the records"""
        return self.records.itervalues()

class _PyDbIndex:
    """Class used for indexing a base on a field
    The instance of Index is an attribute the Base instance"""

    def __init__(self,db,field):
        self.db = db # database object (instance of Base)
        self.field = field # field name

    def __iter__(self):
        return iter(self.db.indices[self.field])

    def keys(self):
        return self.db.indices[self.field].keys()

    def __getitem__(self,key):
        """Lookup by key : return the list of records where
        field value is equal to this key, or an empty list"""
        ids = self.db.indices[self.field].get(key,[])
        return [ self.db.records[_id] for _id in ids ]

