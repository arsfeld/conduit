"""
C{AmazonS3TwoWay} module for synchronizing with I{Amazon Simple Storage
Service} (Amazon S3).

Uses URI relative to base path as LUID. The LUID is also used as key on Amazon
S3.
"""
import logging
log = logging.getLogger("modules.AmazonS3")

import conduit
import conduit.Exceptions as Exceptions
import conduit.utils as Utils
import conduit.datatypes.File as File
import conduit.dataproviders.DataProvider as DataProvider

from boto.s3.connection import S3Connection
from boto.s3.key import Key

MODULES = {"AmazonS3TwoWay" : {"type": "dataprovider"}}

class AmazonS3TwoWay(DataProvider.TwoWay):
    """
    TwoWay dataprovider for synchronizing files with Amazon S3 and vice-versa.
    """

    _name_ = "Amazon S3"
    _description_ = "Synchronize with Amazon S3"
    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "amazon"
    _configurable_ = True

    # default values for class variables (used by self.set_configuration())
    DEFAULT_AWS_ACCESS_KEY = None
    DEFAULT_AWS_SECRET_ACCESS_KEY = None
    DEFAULT_BUCKET_NAME = ""
    DEFAULT_USE_SSL = True

    # set expire time for AWS https links
    AWS_URL_EXPIRE_SECONDS = 60 * 15

    def __init__(self):
        """
        Call base constructor and initialize all variables that are restored
        from configuration.
        """
        DataProvider.TwoWay.__init__(self)

        # configured AWS Access Key
        self.aws_access_key = AmazonS3TwoWay.DEFAULT_AWS_ACCESS_KEY
        # configured AWS Secret Access Key
        self.aws_secret_access_key = \
            AmazonS3TwoWay.DEFAULT_AWS_SECRET_ACCESS_KEY
        # configured name of Amazon S3 bucket
        self.bucket_name = AmazonS3TwoWay.DEFAULT_BUCKET_NAME
        # configuration value determining use of SSL for Amazon S3 connection
        self.use_ssl = AmazonS3TwoWay.DEFAULT_USE_SSL
        # remote keys (equivalent to LUIDs)
        self.keys = []
        # for caching S3Connection object
        self.connection = None
        # for caching Bucket object
        self.bucket = None

    def _data_exists(self, LUID):
        """
        @returns: C{True} if data at the LUID exists, else C{False}.
        """
        return self.bucket.get_key(LUID) != None

    def _get_proxyfile(self, key):
        """
        @param key: Key for which C{ProxyFile} should be returned.
        @type key: C{boto.s3.key.Key}
        @returns: C{ProxyFile} stored under supplied parameter C{key}.
        """
        httpurl = key.generate_url(AmazonS3TwoWay.AWS_URL_EXPIRE_SECONDS)
        # BUG This will fail with "Access denied"
        # (see http://bugzilla.gnome.org/show_bug.cgi?id=545000)
        return File.ProxyFile(
            httpurl,
            key.name,
            Utils.datetime_from_timestamp(long(key.get_metadata("mtime"))),
            long(key.get_metadata("size")))

    def _get_data(self, LUID):
        """
        @returns: ProxyFile object containing remote data with the specified
        LUID.
        """
        key = self.bucket.get_key(LUID)
        return self._get_proxyfile(key)

    def _put_data(self, localfile):
        """
        Uploads the given File object to Amazon S3 and returns its record
        identifier (Rid).

        @returns: Rid of uploaded file.
        """
        filename = localfile.get_relative_uri()
        key = Key(self.bucket)
        # the key's name is the LUID
        key.name = filename
        # add a bit of metadata to key
        # TODO store more metadata: file permissions and owner:group?
        key.set_metadata("size", str(localfile.get_size()))
        key.set_metadata(
            "mtime", str(Utils.datetime_get_timestamp(localfile.get_mtime())))

        # now upload the data
        key.set_contents_from_filename(localfile.get_local_uri())

        # return Rid of uploaded file
        return self._get_proxyfile(key).get_rid()

    def _replace_data(self, LUID, localfile):
        """
        Replaces the remote file identified by LUID with given file object.
        """
        # We don't assign a new LUID when replacing the file, so we can call
        # self._put_data()
        return self._put_data(localfile)

    def _set_aws_access_key(self, key):
        """
        Sets variable C{self.aws_access_key} to given value.
        """
        # set to None if param is the empty string so that boto can figure
        # out the access key by config file or environment variable
        if key == "" or key == "None":
            key = None
        if self.aws_access_key != key:
            self.aws_access_key = key
            # reset connection when configuration changes
            self.connection = None

    def _set_aws_secret_access_key(self, key):
        """
        Sets variable C{self.aws_secret_access_key} to given value.
        """
        # set to None if param is the empty string so that boto can figure
        # out the access key by config file or environment variable
        if key == "" or key == "None":
            key = None
        if self.aws_secret_access_key != key:
            self.aws_secret_access_key = key
            # reset connection when configuration changes
            self.connection = None

    def _set_bucket_name(self, name):
        """
        Sets variable C{self.bucket_name} to given value.

        @param name: Bucket name that C{self.bucket_name} shall be set to.
        @type name: C{str}
        """
        name = str(name)
        if self.bucket_name != name:
            self.bucket_name = name
            # reset bucket when configuration changes
            self.bucket = None

    def _set_use_ssl(self, use_ssl):
        """
        Sets variable C{self.use_ssl}.

        @param use_ssl: C{True} if a secure connection should be used for
                        communication with Amazon S3, C{False} otherwise.
        @type use_ssl: C{bool}
        """
        self.use_ssl = bool(use_ssl)

    def configure(self, window):
        """
        Show configuration dialog for this module.

        @param window: The parent window (used for modal dialogs)
        @type window: C{gtk.Window}
        """
        # lazily import gtk so if conduit is run from command line or a non
        # gtk system, this module will still load. There should be no need
        # to use gtk outside of this function
        import gtk

        def on_dialog_response(sender, response_id):
            """
            Response handler for configuration dialog.
            """
            if response_id == gtk.RESPONSE_OK:
                self._set_aws_access_key(access_key_entry.get_text())
                self._set_aws_secret_access_key(
                    secret_access_key_entry.get_text())
                self._set_bucket_name(bucket_name_entry.get_text())
                self._set_use_ssl((True, False)[ssl_combo_box.get_active()])

        tree = Utils.dataprovider_glade_get_widget(__file__,
                                                   "config.glade",
                                                   "AmazonS3ConfigDialog")

        # get widgets
        dialog = tree.get_widget("AmazonS3ConfigDialog")
        access_key_entry = tree.get_widget("accessKey")
        secret_access_key_entry = tree.get_widget("secretAccessKey")
        bucket_name_entry = tree.get_widget("bucketName")
        ssl_combo_box = tree.get_widget("useSsl")

        # set values of widgets
        access_key_entry.set_text(
            (self.aws_access_key, "")[self.aws_access_key == None])
        secret_access_key_entry.set_text((self.aws_secret_access_key, "")
                                         [self.aws_secret_access_key == None])
        bucket_name_entry.set_text(self.bucket_name)
        ssl_combo_box.set_active((1, 0)[self.use_ssl])

        # show dialog
        Utils.run_dialog_non_blocking(dialog, on_dialog_response, window)

    def _connect(self):
        """
        Connect to Amazon S3 if not already connected and makes sure that
        variable C{self.connection} holds a valid C{S3Connection} object.
        """
        if self.connection != None:
            log.debug("Already connected to Amazon S3.")
        else:
            log.debug("Connecting to Amazon S3.")
            self.connection = S3Connection(self.aws_access_key,
                                           self.aws_secret_access_key,
                                           is_secure=self.use_ssl)

    def _set_bucket(self):
        """
        Makes sure that variable C{self.bucket} holds a valid C{Bucket} object.
        """
        self._connect()
        if self.bucket != None and self.bucket.name == self.bucket_name:
            log.debug("Already have bucket (name = '%s')." % self.bucket.name)
        else:
            log.debug("Getting bucket named '%s'." % self.bucket_name)
            # create or get configured bucket
            # BUG this will fail with environment variable LC_TIME != "en"
            # (see http://code.google.com/p/boto/issues/detail?id=140)
            self.bucket = self.connection.create_bucket(self.bucket_name)

    def refresh(self):
        """
        Connects to Amazon S3 if necessary and gets the name of all keys in the
        configured bucket.
        """
        DataProvider.TwoWay.refresh(self)
        self._set_bucket()
        # Get LUIDs of all remote files (the keys of the remote files are the
        # LUIDs)
        self.keys = [key.name for key in self.bucket]

    def get_all(self):
        """
        Returns the key names (LUIDs) of all remote files.
        @return: A list of string LUIDs.
        """
        DataProvider.TwoWay.get_all(self)
        # refresh() has been called previously, so we can just return self.keys
        return self.keys

    def get(self, LUID):
        """
        Stores remote file identified by supplied LUID locally and returns the
        corresponding File object.
        @param LUID: A LUID which uniquely represents data to return.
        @type LUID: C{str}
        """
        DataProvider.TwoWay.get(self, LUID)
        data = self._get_data(LUID)
        data.force_new_filename(LUID)
        # datatypes can be shared between modules. For this reason it is
        # necessary to explicity set parameters like the LUID
        data.set_UID(LUID)
        return data

    def put(self, localfile, overwrite, LUID):
        """
        Stores the given File object remotely on Amazon S3, if certain
        conditions are met.
        @returns: The Rid of the page at location LUID.
        """
        DataProvider.TwoWay.put(self, localfile, overwrite, LUID)
        # If LUID is None, then we have once-upon-a-time uploaded this file
        if LUID != None:
            # Check if the remote file exists (i.e. has it been deleted)
            if self._data_exists(LUID):
                # The remote file exists
                if not overwrite:
                    # Only replace the data if it is newer than the remote one
                    remotefile = self._get_data(LUID)
                    comp = localfile.compare(remotefile)
                    if comp == conduit.datatypes.COMPARISON_NEWER:
                        return self._replace_data(LUID, localfile)
                    elif comp == conduit.datatypes.COMPARISON_EQUAL:
                        # We are the same, so return either rid
                        return remotefile.get_rid()
                    else:
                        # If we are older than the remote page, or if the two
                        # could not be compared, then we must ask the user what
                        # to do via a conflict
                        raise Exceptions.SynchronizeConflictError(comp,
                                                                  localfile,
                                                                  remotefile)

        # If we get here then the file is new
        return self._put_data(localfile)

    def delete(self, LUID):
        """
        Delete remote file identified by given LUID.
        """
        DataProvider.TwoWay.delete(self, LUID)
        # delete remote file
        self.bucket.delete_key(LUID)

    def get_configuration(self):
        """
        Returns a dict of key-value pairs. Key is the name of an internal
        variable, and value is its current value to save.

        It is important the the key is the actual name (minus the self.) of the
        internal variable that should be restored when the user saves
        their settings.
        """
        return {"aws_access_key" : self.aws_access_key,
                "aws_secret_access_key" : self.aws_secret_access_key,
                "bucket_name" : self.bucket_name,
                "use_ssl" : self.use_ssl}

    def set_configuration(self, config):
        """
        If you override this function then you are responsible for
        checking the sanity of values in the config dict, including setting
        any instance variables to sane defaults
        """
        self._set_aws_access_key(
            config.get("aws_access_key", AmazonS3TwoWay.DEFAULT_AWS_ACCESS_KEY))
        self._set_aws_secret_access_key(
            config.get("aws_secret_access_key",
                       AmazonS3TwoWay.DEFAULT_AWS_SECRET_ACCESS_KEY))
        self._set_bucket_name(
            config.get("bucket_name", AmazonS3TwoWay.DEFAULT_BUCKET_NAME))
        self._set_use_ssl(config.get("use_ssl", AmazonS3TwoWay.DEFAULT_USE_SSL))

    def is_configured(self, isSource, isTwoWay):
        """
        @returns: C{True} if this instance has been correctly configured and
        data can be retrieved/stored into it, else C{False}.
        """
        # Below we also check if the AWS access and secret access key is set.
        # boto is able to retrieve these values from its own config file or
        # from environment variables, and we effectively disable this behavior
        # by checking if these keys are set.
        return self.bucket_name != None and self.aws_access_key != None and \
            self.aws_secret_access_key != None

    def get_UID(self):
        """
        @returns: A string uniquely representing this dataprovider.
        """
        return self.aws_access_key + self.bucket_name
