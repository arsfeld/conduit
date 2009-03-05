"""
BoxDotNet Module
"""
import os, sys
import traceback
import md5
import logging
log = logging.getLogger("modules.BoxDotNet")

import conduit
import conduit.utils as Utils
import conduit.Web as Web
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.File as File

Utils.dataprovider_add_dir_to_path(__file__, "BoxDotNetAPI")
from boxdotnet import BoxDotNet

from gettext import gettext as _

MODULES = {
    "BoxDotNetTwoWay" :          { "type": "dataprovider" }
}

class BoxDotNetTwoWay(DataProvider.TwoWay):

    _name_ = _("Box.net")
    _description_ = _("Synchronize your Box.net files")
    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "boxdotnet"
    _configurable_ = True

    API_KEY="nt0v6a232z6r47iftjx7g0azu6dg4p10"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)

        self.update_configuration(
            foldername = "",
        )
        self.boxapi = None
        self.user_id = None
        self.token = None
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
            log.debug("File [%s] does exist" % fileID)
            return fileID
        else:
            log.debug("File [%s] does not exist" % fileID)
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
    def _upload_file (self, file_path, filename):
        """
        Upload the file to box.net
        @returns: uid of the file
        """
        rsp = self.boxapi.upload(file_path, 
                        auth_token=self.token, 
                        folder_id=self.folder_id, 
                        share=0,
                        filename=filename
                        )

        uid = rsp.files[0].file[0].attrib['id']
        return uid

    def _replace_file (self, fileID, url, name):
        """
        Box.net automatically replaces files with same name, so we can
        use the plain upload method
        @returns: uid of the file
        """
        return self._upload_file(url, name)

    #------------------------------------------
    # File info related functions
    #------------------------------------------
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

    #------------------------------------------
    # Authentication methods
    #------------------------------------------
    def _login(self):
        """
        Logs the user in to box.net
        """
        if self.boxapi == None:
            self.boxapi = BoxDotNet()

        # login if not done yet, we only login once to prevent
        # the browser for popping up each time
        if not self.token:
            # get the ticket and open login url
            self._set_ticket()
            url = BoxDotNet.get_login_url(self.ticket)

            #wait for log in
            Web.LoginMagic("Log into Box.net", url, login_function=self._try_login)

    def _try_login (self):
        """
        Try to perform a login, return None if it does not succeed
        """
        try:
            self._set_login_info(self.ticket)
            return self.token
        except:
            return None

    def _set_ticket(self):
        """
        Get the ticket that can be used for logging in for real
        """
        rsp = self.boxapi.get_ticket(api_key=self.API_KEY)
        self.ticket = rsp.ticket[0].elementText

    def _set_login_info (self, ticket):
        """
        Get a token and the user id
        """
        rsp = self.boxapi.get_auth_token(api_key=self.API_KEY, ticket=ticket)

        self.user_id = rsp.user[0].user_id[0].elementText
        self.token = rsp.auth_token[0].elementText
        self.ticket = None

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

        if LUID == None:
            log.debug("Uploading file URI = %s, Mimetype = %s, Original Name = %s" % (fileURI, mimeType, originalName))
            LUID = self._upload_file (fileURI, originalName)
        else:
            #check if a file exists at that UID
            id = self._get_file_info(LUID)
            if id != None:
                if overwrite == True:
                    log.debug("Replacing file URI = %s, Mimetype = %s, Original Name = %s" % (fileURI, mimeType, originalName))
                    LUID = self._replace_file(LUID, fileURI, originalName)
                else:
                    #Only upload the file if it is newer than the Remote one
                    url = self._get_raw_file_url(id)
                    remoteFile = File.File(url)

                    #this is a limited test for equality type comparison
                    comp = file.compare(remoteFile,True)
                    log.debug("Compared %s with %s to check if they are the same (size). Result = %s" % (file.get_filename(),remoteFile.get_filename(),comp))
                    if comp != conduit.datatypes.COMPARISON_EQUAL:
                        raise Exceptions.SynchronizeConflictError(comp, file, remoteFile)
            
        return self.get(LUID).get_rid()

    def delete(self, LUID):
        """
        Simply call the delete method on the api
        """
        self.boxapi.delete (api_key=BoxDotNetTwoWay.API_KEY, 
                            auth_token=self.token,
                            target='file',
                            target_id=LUID)

    def config_setup(self, config):

        def _login_finished(*args):
            folders = self._get_folders()
            folders_config.set_choices([(f,f) for f in folders])

        def _load_button_clicked(button):
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                                            self,
                                            _login_finished,
                                            self._login)

        config.add_section(_("Folder"))
        folders_config = config.add_item(_("Folder name"), "combotext",
            config_name = "foldername",
            choices = [],
        )
        config.add_item(_("Load folders"), "button",
            initial_value = _load_button_clicked
        )

    def is_configured (self, isSource, isTwoWay):
        return len(self.foldername) > 0

    def get_UID(self):
        return "%s-%s" % (self.user_id, self.foldername)

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        url = self._get_raw_file_url(LUID)
        f = File.File(
                    URI=        url,
                    group=      self.foldername
                    )
        try:
            #gnomevfs doesnt like unicode
            f.force_new_filename(str(self.files[LUID]))
        except KeyError:
            #occurs on put() returning get() because we have
            #not refreshed since. Not a problem because the point
            #of put returning get() is to make the rids() in the same
            #scheme, and not actually do something with the returned file. 
            pass
        f.set_open_URI(url)
        f.set_UID(LUID)

        return f
                
    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.files.keys()
        
    def get_name(self):
        if len(self.foldername) > 0:
            return self.foldername
        else:
            return self._name_


