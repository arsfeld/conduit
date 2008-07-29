import os
import re
import ConfigParser

import conduit.platform

import logging
log = logging.getLogger("Settings")

class SettingsImpl(conduit.platform.Settings):
    """
    Settings implementation which stores settings in an ini style
    format using python config parser library
    """

    VALID_KEY_TYPES = (bool, str, int, list, tuple)

    def __init__(self, defaults, changedCb):
        conduit.platform.Settings.__init__(self, defaults, changedCb)

        self._filePath = os.path.join(conduit.USER_DIR,"settings.ini")

        #convert defaults to strings
        strDefaults = {}
        for k,v in defaults.items():
            strDefaults[k] = str(v)

        self._config = ConfigParser.ConfigParser(defaults=strDefaults)
        self._config.read(self._filePath)

    def get(self, key, default=None):
        #check if the setting has been overridden for this session
        if key in self._overrides:
            val = self._overrides[key]
        else:
            try:
                val = self._config.get('DEFAULT',key)
            except ConfigParser.NoOptionError:
                val = default

        #config parser saves everything to strings, so rely on the defaults
        #for the type information
        if key in self._defaults:
            vtype = type(self._defaults[key])
        else:
            vtype = type(val)

        if val == None:
            log.warn("Unknown key: %s, must specify default value" % key)
            return None

        if vtype not in self.VALID_KEY_TYPES:
            log.warn("Invalid key type: %s" % vtype)
            return None

        #convert list/tuple to list of string values
        if vtype in (list, tuple):
            return eval(val)
        #cast simple types
        else:
            return vtype(val)

    def set(self, key, value):
        if key in self._overrides:
            return True

        if key in self._defaults:
            vtype = type(self._defaults[key])
        else:
            vtype = type(value)

        if vtype not in self.VALID_KEY_TYPES:
            log.warn("Invalid key type: %s" % vtype)
            return False

        #Save every value as a string
        self._config.set('DEFAULT',key, str(value))
        return True

    def proxy_enabled(self):
        """
        @returns: True if the user has specified a http proxy via
        the http_proxy environment variable
        """
        return os.environ.has_key("http_proxy")
        
    def get_proxy(self):
        """
        Returns the details of the configured http proxy. 
        The http_proxy environment variable overrides the GNOME setting
        @returns: host,port,user,password
        """
        if self.proxy_enabled():
            #env vars have preference
            if os.environ.has_key("http_proxy"):
                #re taken from python boto
                pattern = re.compile(
                    '(?:http://)?' \
                    '(?:(?P<user>\w+):(?P<pass>.*)@)?' \
                    '(?P<host>[\w\-\.]+)' \
                    '(?::(?P<port>\d+))?'
                )
                match = pattern.match(os.environ['http_proxy'])
                if match:
                    return (match.group('host'),
                            int(match.group('port')),
                            match.group('user'),
                            match.group('pass'))
        return ("",0,"","")

    def save(self):
        fp = open(self._filePath, 'w')
        self._config.write(fp)
        fp.close()

