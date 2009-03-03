import gconf
import logging
log = logging.getLogger( "modules.DesktopWallpaper")

import conduit
import conduit.utils as Utils
import conduit.dataproviders.File as FileDataProvider
import conduit.dataproviders.DataProvider as DataProvider

MODULES = {
    "DesktopWallpaperDataProvider" : { "type": "dataprovider" }
}

class DesktopWallpaperDataProvider(FileDataProvider.FolderTwoWay):

    _name_ = "Wallpaper"
    _description_ = "Changes your Desktop Wallpaper"
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "preferences-desktop-theme"
    _configurable_ = False

    def __init__(self, *args):
        #Put photos into the users Pictures dir
        pdir = Utils.exec_command_and_return_result("xdg-user-dir", "PICTURES")
        if pdir:
            folder = "file://"+pdir.strip()
        else:
            folder = "file://"+Utils.new_tempdir()

        log.info("Storing pictures in %s" % folder)

        FileDataProvider.FolderTwoWay.__init__(
                            self,
                            folder=folder,
                            folderGroupName="Pictures",
                            includeHidden=False,
                            compareIgnoreMtime=False,
                            followSymlinks=False
                            )

        self._client = gconf.client_get_default()

    def get_UID(self):
        return Utils.get_user_string()

    def put(self, vfsFile, overwrite, LUID=None):
        rid = FileDataProvider.FolderTwoWay.put(self, vfsFile, True, LUID)

        #if the file was successfully transferred then set it
        #as the wallpaper
        if vfsFile.exists():
            self._client.set_string(
                    "/desktop/gnome/background/picture_filename",
                    vfsFile.get_local_uri()
            )

        return rid

    def refresh(self):
        DataProvider.TwoWay.refresh(self)


