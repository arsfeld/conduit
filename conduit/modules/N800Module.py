"""
Provides a number of dataproviders which are associated with
a N800 device.

Copyright: Jaime Frutos Morales , 2007
License: GPLv2
"""
import os
import os.path

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.File as FileDataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

MODULES = {
    "N800Factory" : { "type": "dataprovider-factory" },
}

class N800Factory(DataProvider.DataProviderFactory):
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)

        if kwargs.has_key("hal"):
            self.hal = kwargs["hal"]
            self.hal.connect("n800-added", self._n800_added)
            self.hal.connect("n800-removed", self._n800_removed)

        self.n800s = {}

    def probe(self):
        """ Probe for N800 devices that are already attached """
        for device_type, udi, mount, name in self.hal.get_all_n800s():
            self._n800_added(None, udi, mount, name)

    def _n800_added(self, hal, udi, mount, name):
        """ New N800 has been discovered """
        cat = DataProviderCategory.DataProviderCategory(
                    "Nokia N800",
                    "n800",
                    mount)

        keys = []
        for klass in [N800FolderTwoWay]:
            key = self.emit_added(
                           klass,            # Dataprovider class
                           (mount,udi,),     # Init args
                           cat)              # Category..
            keys.append(key)

        self.n800s[udi] = keys

    def _n800_removed(self, hal, udi, mount, name):
        for key in self.n800s[udi]:
            self.emit_removed(key)

        del self.n800s[udi]

class N800FolderTwoWay(FileDataProvider.FolderTwoWay):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = "N800 Folder"
    _description_ = "Synchronize data to a N800 device"

    DEFAULT_FOLDER = "Backups"
    DEFAULT_GROUP = "N800"
    DEFAULT_HIDDEN = False
    DEFAULT_COMPARE_IGNORE_MTIME = False

    def __init__(self, *args):
        self.mount,self.udi = args
        self.folder = os.path.join(self.mount,N800FolderTwoWay.DEFAULT_FOLDER)

        FileDataProvider.FolderTwoWay.__init__(self,
                self.folder,
                N800FolderTwoWay.DEFAULT_GROUP,
                N800FolderTwoWay.DEFAULT_HIDDEN,
                N800FolderTwoWay.DEFAULT_COMPARE_IGNORE_MTIME
                )

        self.need_configuration(True)

    def refresh(self):
        if not os.path.exists(self.folder):
            try:
                os.mkdir(self.folder)
            except OSError:
                raise Exceptions.RefreshError("Error Creating Directory")

        FileDataProvider.FolderTwoWay.refresh(self)

    def set_configuration(self, config):
        self.folder = config.get("folder", None)
        self.folderGroupName = config.get("folderGroupName", N800FolderTwoWay.DEFAULT_GROUP)
        self.includeHidden = config.get("includeHidden", N800FolderTwoWay.DEFAULT_HIDDEN)
        self.compareIgnoreMtime = config.get("compareIgnoreMtime", N800FolderTwoWay.DEFAULT_COMPARE_IGNORE_MTIME)

        if self.folder != None:
            self.set_configured(True)


    def get_configuration(self):
        return {
            "folder" : self.folder,
            "folderGroupName" : self.folderGroupName,
            "includeHidden" : self.includeHidden,
            "compareIgnoreMtime" : self.compareIgnoreMtime
            }

    def get_UID(self):
        return "%s:%s" % (self.folder, self.folderGroupName)


