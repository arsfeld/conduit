import os.path
import logging
log = logging.getLogger("dataproviders.File")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
from conduit.datatypes import Rid
import conduit.datatypes as DataType
import conduit.datatypes.File as File
import conduit.Utils as Utils
import conduit.Database as DB

TYPE_FILE = "0"
TYPE_FOLDER = "1"

class FileSource(DataProvider.DataSource, Utils.ScannerThreadManager):

    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"
    
    def __init__(self):
        DataProvider.DataSource.__init__(self)
        Utils.ScannerThreadManager.__init__(self)

        #One table stores the top level files and folders (config)
        #The other stores all files to sync. 
        self.db = DB.ThreadSafeGenericDB()
        self.db.create(
                table="config",
                fields=("URI","TYPE","CONTAINS_NUM_ITEMS","SCAN_COMPLETE","GROUP_NAME")
                )
        self.db.create(
                table="files",
                fields=("URI","BASEPATH","GROUPNAME")
                )

    def _add_file(self, f):
        self.db.insert(
                table="config",
                values=(f,TYPE_FILE,0,False,"")
                )

    def _add_folder(self, f, groupname=""):
        self.db.insert(
                table="config",
                values=(f,TYPE_FOLDER,0,False,groupname)
                )

    def initialize(self):
        return True

    def uninitialize(self):
        self.db.close()

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #Make a whole bunch of threads to go and scan the directories
        for oid,uri,groupname in self.db.select("SELECT oid,URI,GROUP_NAME FROM config WHERE TYPE = ?",(TYPE_FOLDER,)):
            self.make_thread(
                    uri, 
                    False,  #FIXME: Dont include hidden?
                    self._on_scan_folder_progress, 
                    self._on_scan_folder_completed, 
                    oid,
                    groupname
                    )
        
        #All threads must complete - otherwise we might miss some items
        self.join_all_threads()

        #now add the single files to the list
        for uri, in self.db.select("SELECT URI FROM config WHERE TYPE = ?",(TYPE_FILE,)):
            self.db.insert(
                        table="files",
                        values=(uri,"","")    #single files dont have basepath and groupname
                        )

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        basepath,group = self.db.select_one("SELECT BASEPATH,GROUPNAME FROM files WHERE URI = ?", (LUID,))
        f = File.File(
                    URI=        LUID,
                    basepath=   basepath,
                    group=      group
                    )
        f.set_open_URI(LUID)
        f.set_UID(LUID)
        return f

    def add(self, LUID):
        f = File.File(URI=LUID)
        if f.exists():
            oid = self.db.select_one("SELECT oid FROM files WHERE URI = ?", (LUID,))
            if oid != None:
                    log.debug("Could not add (already added): %s" % LUID)
                    return False

            if f.is_directory():
                log.debug("Adding folder: %s" % LUID)
                self._add_folder(LUID,"FIXME")
            else:
                log.debug("Adding file: %s" % LUID)
                self._add_file(LUID)
        else:
            log.warn("Could not add: %s" % LUID)
            return False
        return True

    def get_all(self):
        #combine the files contained inside dirs with those the user specified
        files = [f for f, in self.db.select("SELECT URI FROM files")]
        return files

    def finish(self):
        DataProvider.DataSource.finish(self)
        self.db.execute("DELETE FROM files")

    def _on_scan_folder_progress(self, folderScanner, numItems, oid, groupname):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        self.db.update(
                    table="config",
                    oid=oid,
                    CONTAINS_NUM_ITEMS=numItems
                    )

    def _on_scan_folder_completed(self, folderScanner, oid, groupname):
        log.debug("Folder scan complete %s" % folderScanner)
        #Update scan status
        self.db.update(
                    table="config",
                    oid=oid,
                    SCAN_COMPLETE=True,
                    GROUP_NAME=groupname
                    )
        #Put all files into files
        for f in folderScanner.get_uris():
            self.db.insert(
                        table="files",
                        values=(f,folderScanner.baseURI,groupname)
                        )

        self.db.debug(200,True)

class FolderTwoWay(DataProvider.TwoWay):
    """
    TwoWay dataprovider for synchronizing a folder
    """

    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "folder"

    def __init__(self, folder, folderGroupName, includeHidden, compareIgnoreMtime):
        DataProvider.TwoWay.__init__(self)
        self.need_configuration(True)

        self.folder = folder
        self.folderGroupName = folderGroupName
        self.includeHidden = includeHidden
        self.compareIgnoreMtime = compareIgnoreMtime

        self.files = []

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        #scan the folder
        scanThread = Utils.FolderScanner(self.folder, self.includeHidden)
        scanThread.start()
        scanThread.join()

        self.files = scanThread.get_uris()

    def put(self, vfsFile, overwrite, LUID=None):
        """
        Puts vfsFile at the correct location. There are two scenarios
        1) File came from a foreign DP like tomboy
        2) File came from another file dp

        Behaviour:
        1) The foreign DP should have encoded enough information (such as
        the filename) so that we can go ahead and put the file in the dir
        2) First we see if the file has a group attribute. If so, and the
        group matches the groupName here then we put the files into the 
        directory. If not we put the file in the orphan dir. We try and 
        retain the relative path for the files in the specifed group 
        and recreate that in the group dir
        """
        DataProvider.TwoWay.put(self, vfsFile, overwrite, LUID)
        newURI = ""
        if LUID != None:
            newURI = LUID
        elif vfsFile.basePath == "":
            #came from another type of dataprovider such as tomboy
            #where relative path makes no sense. Could also come from
            #the FileSource dp when the user has selected a single file
            log.debug("FolderTwoWay: No basepath. Going to empty dir")
            newURI = self.folder+os.sep+vfsFile.get_filename()
        else:
            #Look for corresponding groups
            if self.folderGroupName == vfsFile.group:
                log.debug("FolderTwoWay: Found corresponding group")
                #put in the folder
                newURI = self.folder+vfsFile.relpath
            else:
                log.debug("FolderTwoWay: Recreating group %s --- %s --- %s" % (vfsFile._get_text_uri(),vfsFile.basePath,vfsFile.group))
                #unknown. Store in the dir but recreate the group
                newURI = self.folder+os.sep+os.path.join(vfsFile.group+vfsFile.relpath)

        destFile = File.File(URI=newURI)
        comp = vfsFile.compare(
                        destFile, 
                        sizeOnly=self.compareIgnoreMtime
                        )
        if overwrite or comp == DataType.COMPARISON_NEWER:
            vfsFile.transfer(newURI, True)

        #FIXME: I think we can return vfsFile.get_rid() because after transfer
        #the file info is reloaded, so we are not permuting anything in place
        #rid = vfsFile.get_rid()
        rid = Rid(
                uid=Utils.uri_make_canonical(newURI), 
                mtime=vfsFile.get_mtime(), 
                hash=vfsFile.get_hash()
                )
        return rid

    def delete(self, LUID):
        f = File.File(URI=LUID)
        if f.exists():
            f.delete()
                
    def get(self, uid):
        DataProvider.TwoWay.get(self, uid)
        f = File.File(
                    URI=uid,
                    basepath=self.folder,
                    group=self.folderGroupName
                    )
        f.set_open_URI(uid)
        f.set_UID(uid)
        return f

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.files

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.files = []

    def add(self, LUID):
        f = File.File(URI=LUID)
        if f.exists() and f.is_directory():
            self.folder = f._get_text_uri()
            self.set_configured(True)
            return True
        return False

