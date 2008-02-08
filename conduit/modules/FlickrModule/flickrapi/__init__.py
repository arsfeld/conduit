#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''A FlickrAPI interface.

See `the FlickrAPI homepage`_ for more info.

.. _`the FlickrAPI homepage`: http://flickrapi.sf.net/
'''

__version__ = '0.16-beta0-CONDUIT'
__revision__ = '$Revision: 114 $'
__all__ = ('FlickrAPI', 'IllegalArgumentException', 'FlickrError',
        'XMLNode', 'set_log_level', '__version__', '__revision__')

# Copyright (c) 2007 by the respective coders, see
# http://flickrapi.sf.net/
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import md5
import urllib
import urllib2
import mimetools
import os.path
import logging
import copy
import webbrowser

from flickrapi.tokencache import TokenCache
from flickrapi.xmlnode import XMLNode
from flickrapi.multipart import Part, Multipart, FilePart
from flickrapi import reportinghttp

LOG = logging.getLogger(__name__)

########################################################################
# Exceptions
########################################################################

class IllegalArgumentException(ValueError):
    '''Raised when a method is passed an illegal argument.
    
    More specific details will be included in the exception message
    when thrown.
    '''

class FlickrError(Exception):
    '''Raised when a Flickr method fails.
    
    More specific details will be included in the exception message
    when thrown.
    '''

########################################################################
# Flickr functionality
########################################################################

def make_utf8(dictionary):
    '''Encodes all Unicode strings in the dictionary to UTF-8. Converts
    all other objects to regular strings.
    
    Returns a copy of the dictionary, doesn't touch the original.
    '''
    
    result = {}

    for (key, value) in dictionary.iteritems():
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        else:
            value = str(value)
        result[key] = value
    
    return result
        

#-----------------------------------------------------------------------
class FlickrAPI:
    """Encapsulated flickr functionality.

    Example usage:

      flickr = FlickrAPI(flickrAPIKey, flickrSecret)
      rsp = flickr.auth_checkToken(api_key=flickrAPIKey, auth_token=token)

    """
    
    flickrHost = "api.flickr.com"
    flickrRESTForm = "/services/rest/"
    flickrAuthForm = "/services/auth/"
    flickrUploadForm = "/services/upload/"
    flickrReplaceForm = "/services/replace/"

    #-------------------------------------------------------------------
    def __init__(self, apiKey, secret=None, fail_on_error=True, username=""):
        """Construct a new FlickrAPI instance for a given API key and secret."""
        
        self.api_key = apiKey
        self.secret = secret
        self.token_cache = TokenCache(apiKey, username)
        self.token = self.token_cache.token
        self.fail_on_error = fail_on_error
        
        self.__handler_cache = {}

    def __repr__(self):
        '''Returns a string representation of this object.'''

        return '[FlickrAPI for key "%s"]' % self.api_key
    __str__ = __repr__
    
    #-------------------------------------------------------------------
    def sign(self, dictionary):
        """Calculate the flickr signature for a set of params.

        data -- a hash of all the params and values to be hashed, e.g.
                {"api_key":"AAAA", "auth_token":"TTTT", "key": u"value".encode('utf-8')}

        """

        data = [self.secret]
        keys = dictionary.keys()
        keys.sort()
        for key in keys:
            data.append(key)
            datum = dictionary[key]
            if isinstance(datum, unicode):
                raise IllegalArgumentException("No Unicode allowed, "
                        "argument %s (%r) should have been UTF-8 by now"
                        % (key, datum))
            data.append(datum)
        
        md5_hash = md5.new()
        md5_hash.update(''.join(data))
        return md5_hash.hexdigest()

    def encode_and_sign(self, dictionary):
        '''URL encodes the data in the dictionary, and signs it using the
        given secret, if a secret was given.
        '''
        
        dictionary = make_utf8(dictionary)
        if self.secret:
            dictionary['api_sig'] = self.sign(dictionary)
        return urllib.urlencode(dictionary)
        
    #-------------------------------------------------------------------
    def __getattr__(self, method):
        """Handle all the regular Flickr API calls.

        >>> flickr.auth_getFrob(apiKey="AAAAAA")
        >>> xmlnode = flickr.photos_getInfo(photo_id='1234')
        >>> json = flickr.photos_getInfo(photo_id='1234', format='json')
        """

        # Refuse to act as a proxy for unimplemented special methods
        if method.startswith('__'):
            raise AttributeError("No such attribute '%s'" % method)

        if self.__handler_cache.has_key(method):
            # If we already have the handler, return it
            return self.__handler_cache.has_key(method)
        
        # Construct the method name and URL
        method = "flickr." + method.replace("_", ".")
        url = "http://" + FlickrAPI.flickrHost + FlickrAPI.flickrRESTForm

        def handler(**args):
            '''Dynamically created handler for a Flickr API call'''

            # Set some defaults
            defaults = {'method': method,
                        'auth_token': self.token,
                        'api_key': self.api_key,
                        'format': 'rest'}
            for key, default_value in defaults.iteritems():
                if key not in args:
                    args[key] = default_value
                # You are able to remove a default by assigning None
                if key in args and args[key] is None:
                    del args[key]

            LOG.debug("Calling %s(%s)" % (method, args))

            post_data = self.encode_and_sign(args)

            flicksocket = urllib.urlopen(url, post_data)
            data = flicksocket.read()
            flicksocket.close()

            # Return the raw response when a non-REST format
            # was chosen.
            if args['format'] != 'rest':
                return data
            
            result = XMLNode.parseXML(data, True)
            if self.fail_on_error:
                FlickrAPI.testFailure(result, True)

            return result

        self.__handler_cache[method] = handler

        return self.__handler_cache[method]
    
    #-------------------------------------------------------------------
    def __get_auth_url(self, perms, frob):
        """Return the authorization URL to get a token.

        This is the URL the app will launch a browser toward if it
        needs a new token.
            
        perms -- "read", "write", or "delete"
        frob -- picked up from an earlier call to FlickrAPI.auth_getFrob()

        """

        encoded = self.encode_and_sign({
                    "api_key": self.api_key,
                    "frob": frob,
                    "perms": perms})

        return "http://%s%s?%s" % (FlickrAPI.flickrHost, \
            FlickrAPI.flickrAuthForm, encoded)

    def upload(self, filename, callback=None, **arg):
        """Upload a file to flickr.

        Be extra careful you spell the parameters correctly, or you will
        get a rather cryptic "Invalid Signature" error on the upload!

        Supported parameters:

        filename -- name of a file to upload
        callback -- method that gets progress reports
        title
        description
        tags -- space-delimited list of tags, '''tag1 tag2 "long tag"'''
        is_public -- "1" or "0"
        is_friend -- "1" or "0"
        is_family -- "1" or "0"

        The callback method should take two parameters:
        def callback(progress, done)
        
        Progress is a number between 0 and 100, and done is a boolean
        that's true only when the upload is done.
        
        For now, the callback gets a 'done' twice, once for the HTTP
        headers, once for the body.
        """

        if not filename:
            raise IllegalArgumentException("filename must be specified")
        
        # verify key names
        required_params = ('api_key', 'auth_token', 'api_sig')
        optional_params = ('title', 'description', 'tags', 'is_public', 
                           'is_friend', 'is_family')
        possible_args = required_params + optional_params
        
        for a in arg.keys():
            if a not in possible_args:
                raise IllegalArgumentException("Unknown parameter "
                        "'%s' sent to FlickrAPI.upload" % a)

        arguments = {'auth_token': self.token, 'api_key': self.api_key}
        arguments.update(arg)

        # Convert to UTF-8 if an argument is an Unicode string
        arg = make_utf8(arguments)
        
        if self.secret:
            arg["api_sig"] = self.sign(arg)
        url = "http://" + FlickrAPI.flickrHost + FlickrAPI.flickrUploadForm

        # construct POST data
        body = Multipart()

        for a in required_params + optional_params:
            if a not in arg:
                continue
            
            part = Part({'name': a}, arg[a])
            body.attach(part)

        filepart = FilePart({'name': 'photo'}, filename, 'image/jpeg')
        body.attach(filepart)

        return self.send_multipart(url, body, callback)
    
    def replace(self, filename, photo_id):
        """Replace an existing photo.

        Supported parameters:

        filename -- name of a file to upload
        photo_id -- the ID of the photo to replace
        """
        
        if not filename:
            raise IllegalArgumentException("filename must be specified")
        if not photo_id:
            raise IllegalArgumentException("photo_id must be specified")

        args = {'filename': filename,
                'photo_id': photo_id,
                'auth_token': self.token,
                'api_key': self.api_key}

        args = make_utf8(args)
        
        if self.secret:
            args["api_sig"] = self.sign(args)
        url = "http://" + FlickrAPI.flickrHost + FlickrAPI.flickrReplaceForm

        # construct POST data
        body = Multipart()

        for arg, value in args.iteritems():
            # No part for the filename
            if value == 'filename':
                continue
            
            part = Part({'name': arg}, value)
            body.attach(part)

        filepart = FilePart({'name': 'photo'}, filename, 'image/jpeg')
        body.attach(filepart)

        return self.send_multipart(url, body)

    def send_multipart(self, url, body, progress_callback=None):
        '''Sends a Multipart object to an URL.
        
        Returns the resulting XML from Flickr.
        '''

        LOG.debug("Uploading to %s" % url)
        request = urllib2.Request(url)
        request.add_data(str(body))
        
        (header, value) = body.header()
        request.add_header(header, value)
        
        if progress_callback:
            response = reportinghttp.urlopen(request, progress_callback)
        else:
            response = urllib2.urlopen(request)
        rspXML = response.read()

        result = XMLNode.parseXML(rspXML)
        if self.fail_on_error:
            FlickrAPI.testFailure(result, True)

        return result

    #-----------------------------------------------------------------------
    @classmethod
    def testFailure(cls, rsp, exception_on_error=True):
        """Exit app if the rsp XMLNode indicates failure."""
        if rsp['stat'] != "fail":
            return
        
        message = cls.getPrintableError(rsp)
        LOG.error(message)
        
        if exception_on_error:
            raise FlickrError(message)

    #-----------------------------------------------------------------------
    @classmethod
    def getPrintableError(cls, rsp):
        """Return a printed error message string."""
        return "%s: error %s: %s" % (rsp.elementName, \
            cls.getRspErrorCode(rsp), cls.getRspErrorMsg(rsp))

    #-----------------------------------------------------------------------
    @classmethod
    def getRspErrorCode(cls, rsp):
        """Return the error code of a response, or 0 if no error."""
        if rsp['stat'] == "fail":
            return rsp.err[0]['code']

        return 0

    #-----------------------------------------------------------------------
    @classmethod
    def getRspErrorMsg(cls, rsp):
        """Return the error message of a response, or "Success" if no error."""
        if rsp['stat'] == "fail":
            return rsp.err[0]['msg']

        return "Success"

    #-----------------------------------------------------------------------
    def validateFrob(self, frob, perms):
        auth_url = self.__get_auth_url(perms, frob)
        webbrowser.open(auth_url, True, True)
        
    #-----------------------------------------------------------------------
    def getTokenPartOne(self, perms="read"):
        """Get a token either from the cache, or make a new one from the
        frob.
        
        This first attempts to find a token in the user's token cache on
        disk. If that token is present and valid, it is returned by the
        method.
        
        If that fails (or if the token is no longer valid based on
        flickr.auth.checkToken) a new frob is acquired.  The frob is
        validated by having the user log into flickr (with a browser).
        
        If the browser needs to take over the terminal, use fork=False,
        otherwise use fork=True.
        
        To get a proper token, follow these steps:
            - Store the result value of this method call
            - Give the user a way to signal the program that he/she has
              authorized it, for example show a button that can be
              pressed.
            - Wait for the user to signal the program that the
              authorization was performed, but only if there was no
              cached token.
            - Call flickrapi.getTokenPartTwo(...) and pass it the result
              value you stored.

        The newly minted token is then cached locally for the next run.

        perms--"read", "write", or "delete"           
    
        An example:
        
        (token, frob) = flickr.getTokenPartOne(perms='write')
        if not token: raw_input("Press ENTER after you authorized this program")
        flickr.getTokenPartTwo((token, frob))
        """
        
        # see if we have a saved token
        token = self.token_cache.token
        frob = None

        # see if it's valid
        if token:
            LOG.debug("Trying cached token '%s'" % token)
            try:
                rsp = self.auth_checkToken(
                        api_key=self.api_key,
                        auth_token=token)

                # see if we have enough permissions
                tokenPerms = rsp.auth[0].perms[0].elementText
                if tokenPerms == "read" and perms != "read": token = None
                elif tokenPerms == "write" and perms == "delete": token = None
            except FlickrError:
                LOG.debug("Cached token invalid")
                self.token_cache.forget()
                token = None
                self.token = None

        # get a new token if we need one
        if not token:
            # get the frob
            LOG.debug("Getting frob for new token")
            rsp = self.auth_getFrob(api_key=self.api_key, auth_token=None)
            self.testFailure(rsp)

            frob = rsp.frob[0].elementText

            # validate online
            self.validateFrob(frob, perms)

        return (token, frob)
        
    def getTokenPartTwo(self, (token, frob)):
        """Part two of getting a token, see getTokenPartOne(...) for details."""

        # If a valid token was obtained, we're done
        if token:
            LOG.debug("getTokenPartTwo: no need, token already there")
            self.token = token
            return token
        
        LOG.debug("getTokenPartTwo: getting a new token for frob '%s'" % frob)
        
        # get a token
        rsp = self.auth_getToken(api_key=self.api_key, frob=frob)
        self.testFailure(rsp)

        token = rsp.auth[0].token[0].elementText
        LOG.debug("getTokenPartTwo: new token '%s'" % token)
        
        # store the auth info for next time
        self.token_cache.token = rsp.xml
        self.token = token

        return token

    #-----------------------------------------------------------------------
    def getToken(self, perms="read"):
        """Use this method if you're sure that the browser process ends
        when the user has granted the autorization - not sooner and
        not later.
        
        This method is deprecated, and will no longer be supported in
        future versions of this API. That's also why we don't tell you
        what it does in this documentation.
        
        Use something this instead:

        (token, frob) = flickr.getTokenPartOne(perms='write')
        if not token: raw_input("Press ENTER after you authorized this program")
        flickr.getTokenPartTwo((token, frob))
        """
        
        LOG.warn("Deprecated method getToken(...) called")
        
        (token, frob) = self.getTokenPartOne(perms)
        return self.getTokenPartTwo((token, frob))


########################################################################
# App functionality
########################################################################

def main():
    '''This is just a demonstration of the FlickrAPI usage.
    For more information, see the package documentation in the 'doc'
    directory.
    '''

    # flickr auth information:
    flickr_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # API key
    flickr_secret = "yyyyyyyyyyyyyyyy"               # shared "secret"

    # make a new FlickrAPI instance
    fapi = FlickrAPI(flickr_key, flickr_secret)

    # do the whole whatever-it-takes to get a valid token:
    (token, frob) = fapi.getTokenPartOne(browser='firefox', perms='write')
    if not token:
        raw_input("Press ENTER after you authorized this program")
    fapi.getTokenPartTwo((token, frob))

    # get my favorites
    rsp = fapi.favorites_getList()
    fapi.testFailure(rsp)

    # and print them
    for photo in rsp.photos[0].photo:
        print "%10(id)s: %(title)s" % photo

    # upload the file foo.jpg
    #rsp = fapi.upload(filename="foo.jpg", \
    #   title="This is the title", description="This is the description", \
    #   tags="tag1 tag2 tag3", is_public="1")
    #if rsp == None:
    #   sys.stderr.write("can't find file\n")
    #else:
    #   fapi.testFailure(rsp)

    return 0

def set_log_level(level):
    '''Sets the log level of the logger used by the FlickrAPI module.
    
    >>> import flicrkapi
    >>> import logging
    >>> flickrapi.set_log_level(logging.INFO)
    '''
    
    LOG.setLevel(level)
    
# run the main if we're not being imported:
if __name__ == "__main__":
    sys.exit(main())

