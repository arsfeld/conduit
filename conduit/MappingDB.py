import os
import os.path
import logging
log = logging.getLogger("MappingDB")


import conduit
import conduit.datatypes
import conduit.utils as Utils
import conduit.Database as Database

DB_FIELDS = ("sourceUID","sourceDataLUID","sourceDataMtime","sourceDataHash","sinkUID","sinkDataLUID","sinkDataMtime","sinkDataHash")
DB_TYPES =  ("TEXT",     "TEXT",          "timestamp",      "TEXT",          "TEXT",   "TEXT",        "timestamp",    "TEXT")
class Mapping(object):
    """
    Manages a mapping of source -> sink
    """
    def __init__(self, oid, sourceUID, sourceRid, sinkUID, sinkRid):
        self.oid = oid
        self.sourceUID = sourceUID
        self.sourceRid = sourceRid
        self.sinkUID = sinkUID
        self.sinkRid = sinkRid
        
    def __str__(self):
        return "%s) [%s] <-> [%s] (%s <-> %s)" % (self.oid,self.sourceRid,self.sinkRid, self.sourceUID, self.sinkUID)

    def get_source_rid(self):
        return self.sourceRid
        
    def set_source_rid(self, rid):
        self.sourceRid = rid
        
    def get_sink_rid(self):
        return self.sinkRid
        
    def set_sink_rid(self, rid):
        self.sinkRid = rid
        
    def values(self):
        return (self.sourceUID,self.sourceRid.get_UID(),self.sourceRid.get_mtime(),self.sourceRid.get_hash(),
                self.sinkUID,self.sinkRid.get_UID(),self.sinkRid.get_mtime(),self.sinkRid.get_hash())
        
class MappingDB:
    """
    Manages mappings of RID <-> RID on a per dataprovider basis.
    Table with 5 fields -
        1. Source Wrapper UID
        2. Source Data LUID
        3. Sink Wrapper UID
        4. Sink Data LUID
        5. Modification Time
    """
    def __init__(self, filename):
        self._open_db(filename)
        
    def _get_mapping_oid(self, sourceUID, dataLUID, sinkUID):
        sql =   "SELECT oid FROM mappings WHERE sourceUID = ? AND sinkUID = ? AND sourceDataLUID = ? " \
                "UNION " \
                "SELECT oid FROM mappings WHERE sourceUID = ? AND sinkUID = ? AND sourceDataLUID = ? " \
                "UNION " \
                "SELECT oid FROM mappings WHERE sourceUID = ? AND sinkUID = ? AND sinkDataLUID = ? " \
                "UNION " \
                "SELECT oid FROM mappings WHERE sourceUID = ? AND sinkUID = ? AND sinkDataLUID = ? "
        params = (  sourceUID,sinkUID,dataLUID,
                    sinkUID,sourceUID,dataLUID,
                    sourceUID,sinkUID,dataLUID,
                    sinkUID,sourceUID,dataLUID
                    )
                    
        oid = self._db.select_one(sql, params)
        if oid == None:
            return None
        else:
            return oid[0]
            
    def _open_db_and_check_structure(self, filename):
        self._db = Database.ThreadSafeGenericDB(filename,detect_types=True)
        if "mappings" not in self._db.get_tables():
            self._db.create(
                    table="mappings",
                    fields=DB_FIELDS,
                    fieldtypes=DB_TYPES
                    )
                    
    def _open_db(self, f):
        """
        Opens the mapping DB at the location @ filename
        """
        filename = os.path.abspath(f)
        try:
            self._open_db_and_check_structure(filename)
        except:
            os.unlink(filename)
            self._open_db_and_check_structure(filename)

    def get_mapping_from_objects(self, LUID1, LUID2, UID):
        
        # Check in both directions, as a conflict resolution can reverse the direction of the mapping
        sql = "SELECT * FROM mappings WHERE (sourceUID = ? OR sinkUID = ? ) AND ((sinkDataLUID = ? AND sourceDataLUID = ?) OR (sourceDataLUID = ? AND sinkDataLUID = ?))"
        res = self._db.select_one(sql, (UID, UID, LUID1, LUID2, LUID1, LUID2))
        
        #a mapping is always returned relative to the source -> sink
        #order in which it was called.
        if (res[5] == UID):
            m = Mapping(
                    res[0],
                    sourceUID=res[1],
                    sourceRid=conduit.datatypes.Rid(res[2],res[3],res[4]),
                    sinkUID=res[5],
                    sinkRid=conduit.datatypes.Rid(res[6],res[7],res[8])
                    )
        else:
            m = Mapping(
                    res[0],
                    sourceUID=res[5],
                    sourceRid=conduit.datatypes.Rid(res[6],res[7],res[8]),
                    sinkUID=res[1],
                    sinkRid=conduit.datatypes.Rid(res[2],res[3],res[4])
                    )

        return m

    def get_mapping(self, sourceUID, dataLUID, sinkUID):
        """
        pass
        """
        oid = self._get_mapping_oid(sourceUID, dataLUID, sinkUID)
        if oid == None:
            m = Mapping(
                    None,
                    sourceUID=sourceUID,
                    sourceRid=conduit.datatypes.Rid(uid=dataLUID),
                    sinkUID=sinkUID,
                    sinkRid=conduit.datatypes.Rid()
                    )
        else:
            sql = "SELECT * FROM mappings WHERE oid = ?"
            res = self._db.select_one(sql, (oid,))
            #a mapping is always returned relative to the source -> sink
            #order in which it was called.
            if (res[1] == sourceUID):
                m = Mapping(
                        res[0],
                        sourceUID=res[1],
                        sourceRid=conduit.datatypes.Rid(res[2],res[3],res[4]),
                        sinkUID=res[5],
                        sinkRid=conduit.datatypes.Rid(res[6],res[7],res[8])
                        )
            else:
                m = Mapping(
                        res[0],
                        sourceUID=res[5],
                        sourceRid=conduit.datatypes.Rid(res[6],res[7],res[8]),
                        sinkUID=res[1],
                        sinkRid=conduit.datatypes.Rid(res[2],res[3],res[4])
                        )
        #FIXME: Remove these...
        #assert(m.sourceUID == sourceUID)
        #assert(m.sinkUID == sinkUID)
        return m

    def get_mappings_for_dataproviders(self, sourceUID, sinkUID):
        """
        Gets all the data mappings for the dataprovider pair
        sourceUID --> sinkUID
        """
        mappings = []
        sql = "SELECT * FROM mappings WHERE sourceUID = ? AND sinkUID = ?"
        for res in self._db.select(sql, (sourceUID, sinkUID)):
            m = Mapping(
                    res[0],
                    sourceUID=res[1],
                    sourceRid=conduit.datatypes.Rid(res[2],res[3],res[4]),
                    sinkUID=res[5],
                    sinkRid=conduit.datatypes.Rid(res[6],res[7],res[8])
                    )
            mappings.append(m)

        return mappings
        
    def save_mapping(self, mapping):
        """
        Saves a mapping between the dataproviders
        """
        if mapping.oid == None:
            #log.debug("New Mapping: %s" % mapping)
            self._db.insert(
                        table="mappings",
                        values=mapping.values()
                        )
        else:
            #log.debug("Update Mapping: %s" % mapping)
            self._db.update(
                        table="mappings",
                        oid=mapping.oid,
                        values=mapping.values()
                        )

    def get_matching_UID(self, sourceUID, dataLUID, sinkUID):
        """
        For a given source and sink pair and a dataLUID from the pair
        find the other matching dataLUID.

        @returns: dataLUID
        """
        oid = self._get_mapping_oid(sourceUID, dataLUID, sinkUID)
        if oid != None:
            sourceDataLUID, sinkDataLUID = self._db.select_one("SELECT sourceDataLUID,sinkDataLUID FROM mappings WHERE oid = ?",(oid,))
            #return the other LUID
            if dataLUID == sourceDataLUID:
                return sinkDataLUID
            elif dataLUID == sinkDataLUID:
                return sourceDataLUID
            else:
                log.warn("Mapping Error")
                return None
        else:
            log.debug("No mapping found for LUID: %s (source: %s, sink %s)" % (dataLUID, sourceUID, sinkUID))
            return None
        
    def delete_mapping(self, mapping):
        """
        Deletes mapping between the dataproviders sourceUID and sinkUID
        that involve dataLUID
        """
        if mapping.oid == None:
            log.warn("Could not delete mapping ")
        self._db.delete(table="mappings",oid=mapping.oid)

    def save(self):
        self._db.save()

    def delete(self):
        self._db.execute("DELETE FROM mappings")

    def debug(self):
        self._db.debug()
        
    def close(self):
        self._db.close()

