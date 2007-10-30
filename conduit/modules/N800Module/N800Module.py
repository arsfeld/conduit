"""
Provides a number of dataproviders which are associated with
a N800 device.

Copyright 2007: Jaime Frutos Morales, John Stowers
License: GPLv2
"""
import os
import os.path

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Video as Video
import conduit.datatypes.Audio as Audio
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
        for klass in [N800FolderTwoWay, N800AudioTwoWay, N800VideoTwoWay]:
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

class N800Base(FileDataProvider.FolderTwoWay):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """
    DEFAULT_GROUP = "N800"
    DEFAULT_HIDDEN = False
    DEFAULT_COMPARE_IGNORE_MTIME = False
    def __init__(self, mount, udi, folder):
        FileDataProvider.FolderTwoWay.__init__(self,
                            folder,
                            N800Base.DEFAULT_GROUP,
                            N800Base.DEFAULT_HIDDEN,
                            N800Base.DEFAULT_COMPARE_IGNORE_MTIME
                            )
        self.need_configuration(False)

    def refresh(self):
        if not os.path.exists(self.folder):
            try:
                os.mkdir(self.folder)
            except OSError:
                raise Exceptions.RefreshError("Error Creating Directory")

        FileDataProvider.FolderTwoWay.refresh(self)

    def get_configuration(self):
        return {
            "folder" : self.folder,
            "folderGroupName" : self.folderGroupName,
            "includeHidden" : self.includeHidden,
            "compareIgnoreMtime" : self.compareIgnoreMtime
            }

    def get_UID(self):
        return "%s:%s" % (self.folder, self.folderGroupName)

class N800FolderTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = "Files"
    _description_ = "Synchronize files/folders o a N800 device"
    _in_type_ = "file"
    _out_type_ = "file"

    DEFAULT_FOLDER = "Backups"

    def __init__(self, *args):
        mount,udi = args
        N800Base.__init__(
                    self,
                    mount,
                    udi,
                    os.path.join(mount,N800FolderTwoWay.DEFAULT_FOLDER)
                    )
        
class N800AudioTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = "Music"
    _description_ = "Synchronizes Music to a N800 device"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "audio-x-generic"

    DEFAULT_FOLDER = "Music"

    def __init__(self, *args):
        mount,udi = args
        N800Base.__init__(
                    self,
                    mount,
                    udi,
                    os.path.join(mount,N800AudioTwoWay.DEFAULT_FOLDER)
                    )
        self.encoding = "ogg"
         
    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        items = [
                    {
                    "Name" : "Format (%s,unchanged)" % ",".join(Audio.PRESET_ENCODINGS.keys()),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()
        
    def get_configuration(self):
        return {'encoding':self.encoding}
        
    def get_input_conversion_args(self):
        try:
            return Audio.PRESET_ENCODINGS[self.encoding]
        except KeyError:
            return {}

class N800VideoTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = "Video"
    _description_ = "Synchronizes Video to a N800 device"
    _in_type_ = "file/video"
    _out_type_ = "file/video"
    _icon_ = "video-x-generic"

    DEFAULT_FOLDER = "Video"

    def __init__(self, *args):
        mount,udi = args
        N800Base.__init__(
                    self,
                    mount,
                    udi,
                    os.path.join(mount,N800VideoTwoWay.DEFAULT_FOLDER)
                    )
        self.encoding = "ogg"
                    
    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        items = [
                    {
                    "Name" : "Format (%s,unchanged)" % ",".join(Video.PRESET_ENCODINGS.keys()),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()
        
    def get_configuration(self):
        return {'encoding':self.encoding}
        
    def get_input_conversion_args(self):
        try:
            return Video.PRESET_ENCODINGS[self.encoding]
        except KeyError:
            return {}
        

