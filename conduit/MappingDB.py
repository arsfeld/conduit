import os, os.path

import conduit
import conduit.Utils as Utils
import conduit.DB as DB
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
    def __init__(self, filename=None):
        self._db = None
        self.open_db(filename)

    def _open_db(self,f):
        """
        Blindly opens the mappingDB. Throws exceptions if the db is corrupt
        """
        self._db = DB.SimpleDb(f)
        self._db.create("sourceUID","sourceDataLUID", "sourceDataMtime", "sinkUID", "sinkDataLUID", "sinkDataMtime", mode="open")
        #We access the DB via all fields so all need indices
        self._db.create_index(*self._db.fields)

    def _get_mapping(self, sourceUID, sourceDataLUID, sinkUID):
        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                return i

        existing = self.get_mappings_for_dataproviders(sinkUID,sourceUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                return i

        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sinkDataLUID"] == sourceDataLUID:
                return i

        existing = self.get_mappings_for_dataproviders(sinkUID,sourceUID)
        for i in existing:
            if i["sinkDataLUID"] == sourceDataLUID:
                return i

        return None

    def get_mappings_for_dataproviders(self, sourceUID, sinkUID):
        """
        Gets all the data mappings for the dataprovider pair
        sourceUID <--> sinkUID
        """
        return [i for i in self._db if i["sourceUID"] == sourceUID and i["sinkUID"] == sinkUID]
        
    def open_db(self, f):
        """
        Opens the mapping DB at the location @ filename
        """
        if f == None:
            return

        filename = os.path.abspath(f)
        try:
            self._open_db(filename)
        except:
            logw("Mapping DB has become corrupted, deleting")
            if os.path.exists(filename) and os.path.isfile(filename):
                os.unlink(filename)

            self._open_db(filename)

    def save_mapping(self, sourceUID, sourceDataLUID, sourceDataMtime, sinkUID, sinkDataLUID, sinkDataMtime):
        """
        Saves a mapping between the dataproviders with sourceUID and sinkUID
        The mapping says that within that syncronization pair the two data
        items sourceeDataLUID and sinkDataLUID are synchronized
        """
        if None in [sourceUID, sourceDataLUID, sinkUID, sinkDataLUID]:
            logw("Could not save mapping (%s,%s,%s,%s)" % (sourceUID, sourceDataLUID, sinkUID, sinkDataLUID))
            return

        existing = self._get_mapping(sourceUID, sourceDataLUID, sinkUID)
        if existing != None:
            logd("Updating mapping: %s --> %s" % (sourceDataLUID,sinkDataLUID))
            if sourceUID == existing['sourceUID']:
                self._db.update(
                    existing,
                    sourceDataLUID=sourceDataLUID,
                    sourceDataMtime=sourceDataMtime,
                    sinkDataLUID=sinkDataLUID,
                    sinkDataMtime=sinkDataMtime
                    )
            else:
                self._db.update(
                    existing,
                    sourceDataLUID=sinkDataLUID,
                    sourceDataMtime=sinkDataMtime,
                    sinkDataLUID=sourceDataLUID,
                    sinkDataMtime=sourceDataMtime
                    )
        else:
            logd("Saving new mapping: %s --> %s" % (sourceDataLUID,sinkDataLUID))
            self._db.insert(
                        sourceUID=sourceUID,
                        sourceDataLUID=sourceDataLUID,
                        sourceDataMtime=sourceDataMtime,
                        sinkUID=sinkUID,
                        sinkDataLUID=sinkDataLUID,
                        sinkDataMtime=sinkDataMtime
                        )

    def get_matching_UID(self, sourceUID, sourceDataLUID, sinkUID):
        """
        For a given source and sink pair, get the mapping data for
        the sourceDataLUID. 

        @returns: dataLUID
        """
        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                return i["sinkDataLUID"]

        existing = self.get_mappings_for_dataproviders(sinkUID,sourceUID)
        for i in existing:
            if i["sourceDataLUID"] == sourceDataLUID:
                return i["sinkDataLUID"]

        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sinkDataLUID"] == sourceDataLUID:
                return i["sourceDataLUID"]

        existing = self.get_mappings_for_dataproviders(sinkUID,sourceUID)
        for i in existing:
            if i["sinkDataLUID"] == sourceDataLUID:
                return i["sourceDataLUID"]

        logd("No mapping found for LUID: %s (source: %s, sink %s)" % (sourceDataLUID, sourceUID, sinkUID))

        return None


    def delete_mapping(self, sourceUID, sinkUID, dataLUID):
        """
        Deletes mapping between the dataproviders sourceUID and sinkUID
        that involve dataLUID

        @returns: The number of mappings deleted
        """
        if dataLUID == None:
            logw("Could not delete NULL mapping %s <--> %s" % (sourceUID, sinkUID))
            return 0

        delete = []
        existing = self.get_mappings_for_dataproviders(sourceUID,sinkUID)
        for i in existing:
            if i["sinkDataLUID"] == dataLUID or i["sourceDataLUID"] == dataLUID:
                delete.append(i)

        num = self._db.delete(delete)
        logd("%s mappings deleted for mapping %s <--> %s" % (num, sourceUID, sinkUID))
        return num

    def save(self):
        logd("Saving mapping DB to %s" % self._db.name)
        self._db.commit()

    def delete(self):
        """
        Empties the database
        """
        logd("Empty the DB")
        self._db.delete(self._db)
        self._db.commit()

    def debug(self, printMtime=False):
        s = "Contents of MappingDB: %s\n" % self._db.name
        sources = [i["sourceUID"] for i in self._db]
        sources = Utils.distinct_list(sources)
        for sourceUID in sources:
            #all matching sinkUIDs for sourceUID
            sinks = [i["sinkUID"] for i in self._db if i["sourceUID"] == sourceUID]
            sinks = Utils.distinct_list(sinks)
            for sinkUID in sinks:
                s += "\t%s --> %s\n" % (sourceUID, sinkUID)
                #get relationships
                rels = self.get_mappings_for_dataproviders(sourceUID, sinkUID)
                for r in rels:
                    if printMtime:
                        s += "\t\t%s (%s) --> %s (%s)\n" % (r["sourceDataLUID"], r["sourceDataMtime"], r["sinkDataLUID"], r["sinkDataMtime"])
                    else:
                        s += "\t\t%s --> %s\n" % (r["sourceDataLUID"], r["sinkDataLUID"])
        return s
