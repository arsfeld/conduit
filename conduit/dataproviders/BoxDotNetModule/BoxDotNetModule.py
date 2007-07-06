"""
BoxDotNet Module
"""
import os, sys
import gtk
import traceback
import md5


import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File

Utils.dataprovider_add_dir_to_path(__file__, "BoxDotNetAPI")
from boxdotnet import BoxDotNet

MODULES = {
    "BoxDotNetTwoWay" :          { "type": "dataprovider" }
}

class BoxDotNetTwoWay(DataProvider.TwoWay):

    _name_ = "Box.net"
    _description_ = "Sync Your Box.net files"
    _category_ = DataProvider.CATEGORY_FILES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "boxdotnet"

    API_KEY="nt0v6a232z6r47iftjx7g0azu6dg4p10"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.need_configuration(True)

        self.boxapi = None
        self.user_id = None
        self.token = None
        self.foldername = ""
        self.folder_id = None

        self.files = {}

    #------------------------------------------
    # File info related functions
    #------------------------------------------
    def _get_file_info(self, fileID):
        """
        Returns the id, if the id is present in the configured folder
        """
        self.files = self._get_files(self.folder_id)

        if self.files.has_key(fileID):
            logd("File [%s] does exist" % fileID)
            return fileID
        else:
            logd("File [%s] does not exist" % fileID)
            return None

    def _get_files(self,folderID):
        """
        Gets a list of files present in the configured folder
        """
        rsp = self.boxapi.get_account_tree (api_key=BoxDotNetTwoWay.API_KEY,
                                            auth_token=self.token,
                                            folder_id=folderID,
                                            params=['nozip'])
        files = {}

        try:
            for file in rsp.tree[0].folder[0].files[0].file:
                files[file.attrib['id']] = file.attrib['file_name']
        finally:
            return files

    def _get_raw_file_url(self, fileID):
        """
        Format an url that can be used for downloading a file
        """
        return "http://box.net/api/1.0/download/%s/%s" % (self.token, fileID)

    #------------------------------------------
    # Upload functions
    #------------------------------------------
    def _upload_file (self, url, name):
        """
        Upload the file to url
        """
        rsp = self.boxapi.upload(filename=url, auth_token=self.token, folder_id=self.folder_id, share=0)

        return rsp.files[0].file[0].attrib['id']

    def _replace_file (self, fileID, url, name):
        """
        Box.net automatically replaces files with same name, so we can
        use the plain upload method
        """
        return self._upload_file(url, name)

    #------------------------------------------
    # File info related functions
    #------------------------------------------
    def _set_login_info (self, xml):
        """
        Read the user id and the auth_token from the xml node
        """
        self.user_id = xml.user[0].user_id[0].elementText
        self.token = xml.auth_token[0].elementText

    def _get_folder_id(self):
        """
        Returns a folder id for the configured folder name, it re-uses existing ones
        and creates a new folder if it isn't present
        """
        id = None

        # see if folder already exists
        folders = self._get_folders()

        if folders.has_key (self.foldername):
            id = folders[self.foldername]

        # return if it does
        if id:
            return id
        # create otherwise
        else:
            return self._create_folder ()

    def _get_folders(self):
        """
        Returns a dictionary of name-id representing the upper-level
        folders
        """
        rsp = self.boxapi.get_account_tree(api_key=BoxDotNetTwoWay.API_KEY,
                                           auth_token=self.token,
                                           folder_id=0,
                                           params=['nozip'])

        folders = {}

        try:
            # this might throw an exception if user has no folders yet
            for folder in rsp.tree[0].folder[0].folders[0].folder:
                folders[folder.attrib['name']] = folder.attrib['id']
        finally:
            return folders

    def _create_folder(self):
        """
        Create a top-level folder with the configured name, and return the id
        """
        rsp = self.boxapi.create_folder(api_key=BoxDotNetTwoWay.API_KEY,
                                        auth_token=self.token,
                                        parent_id=0,
                                        name=self.foldername,
                                        share=0)

        return rsp.folder[0].folder_id[0].elementText

    def _login(self):
        if self.boxapi == None:
            self.boxapi = BoxDotNet(browser="gnome-www-browser -p")

        # login if not done yet, we only login once to prevent
        # the browser for popping up each time
        if not self.token:
            rsp = self.boxapi.login(BoxDotNetTwoWay.API_KEY)
            self._set_login_info(rsp)

    #------------------------------------------
    # Dataprovider Functions
    #------------------------------------------
    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self._login()

        # set folder id if not done yet or configuration changed
        folder_id = self._get_folder_id()

        if not self.folder_id or self.folder_id != folder_id: 
            self.folder_id = folder_id

        self.files = self._get_files(self.folder_id)

    def put (self, file, overwrite, LUID=None):
        """
        Puts the file in the sink, this uploads the file if it is not present yet
        or updates it if necessary
        """
        DataProvider.TwoWay.put(self, file, overwrite, LUID)

        originalName = file.get_filename()
        #Gets the local URI (/foo/bar). If this is a remote file then
        #it is first transferred to the local filesystem
        fileURI = file.get_local_uri()

        mimeType = file.get_mimetype()
        
        #Check if we have already uploaded the file
        if LUID != None:
            id = self._get_file_info(LUID)
            #check if a file exists at that UID
            if id:
                if overwrite == True:
                    #replace the file
                    return self._replace_file(LUID, fileURI, originalName)
                else:
                    #Only upload the file if it is newer than the Remote one
                    url = self._get_raw_file_url(id)
                    remoteFile = File.File(url)

                    #this is a limited test for equality type comparison
                    comp = file.compare(remoteFile,True)
                    logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                            (file.get_filename(),remoteFile.get_filename(),comp))
                    if comp != conduit.datatypes.COMPARISON_EQUAL:
                        raise Exceptions.SynchronizeConflictError(comp, file, remoteFile)
                    else:
                        return LUID

        logd("Uploading file URI = %s, Mimetype = %s, Original Name = %s" % (fileURI, mimeType, originalName))

        #upload the file
        return self._upload_file (fileURI, originalName)

    def delete(self, LUID):
        """
        Simply call the delete method on the api
        """
        self.boxapi.delete (api_key=BoxDotNetTwoWay.API_KEY, 
                            auth_token=self.token,
                            target='file',
                            target_id=LUID)


    def configure(self, window):
        """
        Configures the BoxDotNet sink
        """
        tree = Utils.dataprovider_glade_get_widget(
                        __file__,
                        "config.glade",
                        "BoxDotNetConfigDialog")

        #get a whole bunch of widgets
        foldername = tree.get_widget("foldername")

        #preload the widgets
        foldername.set_text(self.foldername)

        dlg = tree.get_widget("BoxDotNetConfigDialog")
        dlg.set_transient_for(window)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            # get the values from the widgets
            self.foldername = foldername.get_text()

            #user must enter their username
            self.set_configured(self.is_configured())

        dlg.destroy()

    def is_configured (self):
        return len (self.foldername) > 0

    def get_configuration(self):
        return {
            "foldername" : self.foldername
            }

    def get_UID(self):
        return "%s-%s" % (self.user_id, self.foldername)

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        url = self._get_raw_file_url(LUID)
        f = File.File(
                    URI=        url,
                    group=      self.foldername
                    )
        #FIXME: gnomevfs doesnt like unicode
        f.force_new_filename(str(self.files[LUID]))
        f.set_open_URI(url)
        f.set_UID(LUID)

        return f
                
    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.files.keys()


