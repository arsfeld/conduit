"""
Provides a number of dataproviders which are associated with
a N800 device.

Copyright 2007: Jaime Frutos Morales, John Stowers
License: GPLv2
"""
import os
import os.path
import logging
log = logging.getLogger("modules.N800")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Video as Video
import conduit.datatypes.Audio as Audio
import conduit.datatypes.Photo as Photo
import conduit.dataproviders.VolumeFactory as VolumeFactory
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.File as FileDataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

MODULES = {
    "N800Factory" : { "type": "dataprovider-factory" },
}


class N800Factory(VolumeFactory.VolumeFactory):
    def is_interesting(self, udi, props):
        if props.has_key("info.parent") and props.has_key("info.parent")!="":
            prop2 = self._get_properties(props["info.parent"])
            if prop2.has_key("storage.model") and prop2["storage.model"]=="N800":
                if prop2.has_key("storage.removable") and prop2["storage.removable"] == True:
                    return True
        return False

    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    "Nokia N800",
                    "n800",
                    kwargs['mount'])

    def get_dataproviders(self, udi, **kwargs):
         return [N800FolderTwoWay, N800AudioTwoWay, N800VideoTwoWay, N800PhotoTwoWay]


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

    def _simple_configure(self, window, encodings):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        items = [
                    {
                    "Name" : "Format (%s,unchanged)" % ",".join(encodings),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

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

    _name_ = "N800 Files"
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

    _name_ = "N800 Music"
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
        self._simple_configure(window, Audio.PRESET_ENCODINGS.keys())

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

    _name_ = "N800 Videos"
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
        self._simple_configure(window, Video.PRESET_ENCODINGS.keys())
        
    def get_configuration(self):
        return {'encoding':self.encoding}
        
    def get_input_conversion_args(self):
        try:
            return Video.PRESET_ENCODINGS[self.encoding]
        except KeyError:
            return {}
        
class N800PhotoTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = "N800 Photos"
    _description_ = "Synchronizes Video to a N800 device"
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"
    _icon_ = "image-x-generic"

    DEFAULT_FOLDER = "Photo"
    PRESET_ENCODINGS = {
        "jpeg":{'formats':'image/jpeg','default-format':'image/jpeg','size':'800x480'},
        "png":{'formats':'image/png','default-format':'image/png','size':'800x480'}
        }

    def __init__(self, *args):
        mount,udi = args
        N800Base.__init__(
                    self,
                    mount,
                    udi,
                    os.path.join(mount,N800PhotoTwoWay.DEFAULT_FOLDER)
                    )
        self.encoding = "jpg"
                    
    def configure(self, window):
        self._simple_configure(window, N800PhotoTwoWay.PRESET_ENCODINGS.keys())
        
    def get_configuration(self):
        return {'encoding':self.encoding}
        
    def get_input_conversion_args(self):
        try:
            return N800PhotoTwoWay.PRESET_ENCODINGS[self.encoding]
        except KeyError:
            return {}

