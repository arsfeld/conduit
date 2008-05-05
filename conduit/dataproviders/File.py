import os.path
import logging
import ConfigParser
log = logging.getLogger("dataproviders.File")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes as DataType
import conduit.datatypes.File as File
import conduit.Vfs as Vfs
import conduit.Database as DB
import conduit.Exceptions as Exceptions

TYPE_FILE = "0"
TYPE_FOLDER = "1"

def is_on_removable_volume(folderUri):
    return Vfs.uri_is_on_removable_volume(folderUri)
    
def get_removable_volume_info(folderUri):
    """
    Returns the root uri of the volume, and local path of the 
    group config file
    """
    rooturi = Vfs.uri_get_volume_root_uri(folderUri)
    path = Vfs.uri_join(
                Vfs.uri_to_local_path(rooturi),
                ".conduit")
    return rooturi,path
    
def save_removable_volume_group_file(folderUri, folderGroupName):
    """
    Saves a file on the root of the drive, in ini format, 
    containing the uri and group
    
    e.g.
    [DEFAULT]
    relative/uri/from/volume/root = group name
    """
    if is_on_removable_volume(folderUri):
        #write to the /volume/root/.conduit file
        rooturi,path = get_removable_volume_info(folderUri)
        conf = ConfigParser.SafeConfigParser()
        conf.read(path)
        
        log.debug("Saving group (%s = %s) to %s" % (folderUri,folderGroupName,path))
        conf.set(
            "DEFAULT",
            folderUri.replace(rooturi,""),
            folderGroupName
            )
        fp = open(path, 'w')
        conf.write(fp)
        fp.close()
        return True
    return False

def read_removable_volume_group_file(folderUri):
    items = []
    if is_on_removable_volume(folderUri):
        #read from the /volume/root/.conduit file
        rooturi,path = get_removable_volume_info(folderUri)
        conf = ConfigParser.SafeConfigParser()
        conf.read(path)
        for p,n in conf.items("DEFAULT"):
            log.debug("Read group (%s = %s)" % (p,n))
            #check the path still exists on the volume
            if Vfs.uri_exists(rooturi+p):
                items.append((p,n))
    return items

class FileSource(DataProvider.DataSource, Vfs.FolderScannerThreadManager):

    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"
    
    def __init__(self):
        DataProvider.DataSource.__init__(self)
        Vfs.FolderScannerThreadManager.__init__(self)

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
        self.db.execute("DELETE FROM files")
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
        for oid,uri in self.db.select("SELECT oid,URI FROM config WHERE TYPE = ?",(TYPE_FILE,)):
            f = File.File(URI=uri)
            if f.exists():
                self.db.insert(
                            table="files",
                            values=(uri,"","")    #single files dont have basepath and groupname
                            )
            else:
                self.db.delete(
                    table="config",
                    oid=oid
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

    def finish(self, aborted, error, conflict):
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

class FolderTwoWay(DataProvider.TwoWay):
    """
    TwoWay dataprovider for synchronizing a folder
    """

    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "folder"

    def __init__(self, folder, folderGroupName, includeHidden, compareIgnoreMtime, followSymlinks):
        DataProvider.TwoWay.__init__(self)
        self.folder = folder
        self.folderGroupName = folderGroupName
        self.includeHidden = includeHidden
        self.compareIgnoreMtime = compareIgnoreMtime
        self.followSymlinks = followSymlinks

        self.fstype = None
        self.files = []
        
    def _transfer_file(self, vfsFile, newURI, overwrite):
        try:
            vfsFile.transfer(newURI, overwrite)
        except File.FileTransferError:
            raise Exceptions.SyncronizeFatalError("Transfer Cancelled")
        
    def initialize(self):
        return True

    def is_configured(self, isSource, isTwoWay):
        return Vfs.uri_exists(self.folder)

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        #cache the filesystem type for speed
        self.fstype = Vfs.uri_get_filesystem_type(self.folder)

        #scan the folder
        scanThread = Vfs.FolderScanner(self.folder, self.includeHidden, self.followSymlinks)
        scanThread.start()
        scanThread.join()
        self.files = scanThread.get_uris()

    def put(self, vfsFile, overwrite, LUID=None):
        """
        Puts vfsFile at the correct location. There are three scenarios
        1) File came from a foreign DP like tomboy
        2) File came from another file dp

        Behaviour:
        1) The foreign DP should have encoded enough information (such as
        the filename) so that we can go ahead and put the file in the dir
        2) First we see if the file has a group attribute.
            a) If so, and the group matches the groupName here then we 
            put the files into the directory.
            b) If not we put the file in a subdir by the name of the group 
            
        We always retain the relative path for the files
        """
        DataProvider.TwoWay.put(self, vfsFile, overwrite, LUID)
        newURI = ""
        if LUID != None:
            newURI = LUID
        elif vfsFile.basePath == "":
            #came from another type of dataprovider such as tomboy
            #where relative path makes no sense. Could also come from
            #the FileSource dp when the user has selected a single file
            log.debug("No basepath. Going to empty dir")
            newURI = Vfs.uri_join(self.folder,vfsFile.get_filename())
        else:
            #Look for corresponding groups
            relpath = vfsFile.get_relative_uri()
            log.debug("Relative path: %s" % relpath)
            if self.folderGroupName == vfsFile.group:
                log.debug("Found corresponding group")
                #put in the folder
                newURI = Vfs.uri_join(self.folder,relpath)
            else:
                log.debug("Recreating group: %s" % vfsFile.group)
                #unknown. Store in the dir but recreate the group
                newURI = Vfs.uri_join(self.folder,vfsFile.group,relpath)

        #escape illegal filesystem characters
        if self.fstype:
            newURI = Vfs.uri_sanitize_for_filesystem(newURI, self.fstype)
            
        #overwrite is the easy case, as for it to be true, requires specific user
        #interaction
        if overwrite == True:
            self._transfer_file(vfsFile, newURI, overwrite)
        else:
            #check for conflicts
            destFile = File.File(URI=newURI)
            if destFile.exists():
                comp = vfsFile.compare(
                            destFile, 
                            sizeOnly=self.compareIgnoreMtime
                            )
                if LUID != None and comp == DataType.COMPARISON_NEWER:
                    self._transfer_file(vfsFile, newURI, overwrite)
                elif comp == DataType.COMPARISON_EQUAL:
                    pass
                else:
                    raise Exceptions.SynchronizeConflictError(comp, vfsFile, destFile)
            else:
                self._transfer_file(vfsFile, newURI, overwrite)                    

        return self.get(newURI).get_rid()

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

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        self.files = []
        try:
            #Save the .group file to the root of this volume (if it is removable)
            save_removable_volume_group_file(self.folder, self.folderGroupName)
        except Exception, e:
            log.warn("Error saving volume group file: %s" % e)

    def add(self, LUID):
        f = File.File(URI=LUID)
        if f.exists() and f.is_directory():
            self.folder = f._get_text_uri()
            return True
        return False

