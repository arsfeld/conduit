"""
Provides a number of dataproviders which are associated with
a N800 device. Allow the transcoding of music, photos and video before 
transferring them to the n800

Copyright 2007: Jaime Frutos Morales, John Stowers
License: GPLv2
"""
import logging
log = logging.getLogger("modules.N800")

import conduit
import conduit.datatypes.File as File
import conduit.datatypes.Video as Video
import conduit.datatypes.Audio as Audio
import conduit.datatypes.Photo as Photo
import conduit.dataproviders.VolumeFactory as VolumeFactory
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.File as FileDataProvider
import conduit.Exceptions as Exceptions
import conduit.Vfs as Vfs

from gettext import gettext as _

MODULES = {
    "N800Factory" : { "type": "dataprovider-factory" },
}


class N800Factory(VolumeFactory.VolumeFactory):
    def is_interesting(self, udi, props):
        if props.has_key("info.parent") and props.has_key("info.parent")!="":
            prop2 = self._get_properties(props["info.parent"])
            if prop2.has_key("storage.model") and prop2["storage.model"] in ("N800", "N810"):
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
    
    #Translators: Translate this in derived classes.
    DEFAULT_FOLDER = _("Conduit")
    #Translators: Format string used to describe the acceptable formats the 
    #device accepts. The first arg is replaced with DEFAULT_FOLDER and the second
    #arg is a comma seperated list of encodings
    FORMAT_CONVERSION_STRING = _("%s Format (%s)")
    #Signifies that a conversion should not take place
    NO_CONVERSION_STRING = _("unchanged")

    _configurable_ = True

    def __init__(self, mount, udi, folder):
        FileDataProvider.FolderTwoWay.__init__(self,
                            "file://"+folder,
                            "N800",
                            False,
                            False,
                            False
                            )
        self.mount = mount
        self.udi = udi
        self.encodings =  {}
        self.encoding = ""

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        encodings = self.encodings.keys()+[self.NO_CONVERSION_STRING]
        items = [
                    {
                    "Name" : self.FORMAT_CONVERSION_STRING % (self.DEFAULT_FOLDER, ",".join(encodings)),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def refresh(self):
        d = File.File(URI=self.folder)
        if not d.exists():
            try:
                d.make_directory_and_parents()
            except:
                raise Exceptions.RefreshError("Error Creating Directory")
        FileDataProvider.FolderTwoWay.refresh(self)
        
    def get_input_conversion_args(self):
        try:
            return self.encodings[self.encoding]
        except KeyError:
            return {}
            
    def get_configuration(self):
        return {'encoding':self.encoding}

    def get_UID(self):
        return "%s" % self.udi

class N800FolderTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = _("N800 Files")
    _description_ = _("Synchronizes files/folders to a N800 device")
    _in_type_ = "file"
    _out_type_ = "file"

    #To translators: default backup folder of N800
    DEFAULT_FOLDER = _("Backups")

    def __init__(self, *args):
        N800Base.__init__(
                    self,
                    mount=args[0],
                    udi=args[1],
                    folder=Vfs.uri_join(args[0],self.DEFAULT_FOLDER)
                    )
                    
class N800AudioTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = _("N800 Music")
    _description_ = _("Synchronizes music to a N800 device")
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "audio-x-generic"

    #To translators: defaul music folder of N800
    DEFAULT_FOLDER = _("Music")

    def __init__(self, *args):
        N800Base.__init__(
                    self,
                    mount=args[0],
                    udi=args[1],
                    folder=Vfs.uri_join(args[0],self.DEFAULT_FOLDER)
                    )
        self.encodings =  Audio.PRESET_ENCODINGS.copy()
        self.encoding = "ogg"
         
class N800VideoTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = _("N800 Videos")
    _description_ = _("Synchronizes video to a N800 device")
    _in_type_ = "file/video"
    _out_type_ = "file/video"
    _icon_ = "video-x-generic"

    #To translators: defaul video folder of N800
    DEFAULT_FOLDER = _("Video")

    def __init__(self, *args):
        N800Base.__init__(
                    self,
                    mount=args[0],
                    udi=args[1],
                    folder=Vfs.uri_join(args[0],self.DEFAULT_FOLDER)
                    )
        self.encodings =  Video.PRESET_ENCODINGS.copy()
        self.encoding = "ogg"
                    
class N800PhotoTwoWay(N800Base):
    """
    TwoWay dataprovider for synchronizing a folder on a N800
    """

    _name_ = _("N800 Photos")
    _description_ = _("Synchronizes video to a N800 device")
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"
    _icon_ = "image-x-generic"

    #To translators: default photos folder of N800
    DEFAULT_FOLDER = _("Photo")

    def __init__(self, *args):
        N800Base.__init__(
                    self,
                    mount=args[0],
                    udi=args[1],
                    folder=Vfs.uri_join(args[0],self.DEFAULT_FOLDER)
                    )
        self.encodings =  Photo.PRESET_ENCODINGS.copy()
        #Add size = 800x480 to the default photo encodings
        for k in self.encodings.keys():
            self.encodings[k]['size'] = '800x480'
        self.encoding = "jpeg"
                    

