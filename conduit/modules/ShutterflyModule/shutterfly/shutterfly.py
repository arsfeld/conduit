##  Lots of code based on code of Pycasaweb by:
##    Copyright (C) 2006 manatlan manatlan[at]gmail(dot)com
##
##  Changes to use new gdata api by:
##    Copyright (C) 2007 thomas.vanmachelen@gmail.com
##
##  Changes to implement api interface to Shutterfly by:
##		Copyright (C) 2007 jasl8r@gmail.com
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 2 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
"""
Shutterfly data API
"""

import urllib, urllib2
import cookielib
from urlparse import urlparse
from cgi import parse_qs
import re
import time
import os

from gettext import gettext as _

FORMAT_STRING = _("%Y-%m-%d %H:%M:%S")
PERPAGE = 80									# Shutterfly shows 80 pics per small page

###############################################################################
# Helper functions
###############################################################################
def utf8(v):
	""" ensure to get 'v' in an UTF8 encoding (respect None) """
	if v != None:
		if type(v) != unicode:	
			v = unicode(v, "utf_8", "replace")
		v = v.encode("utf_8")
	return v

def mkRequest(url, data=None, headers={}):
	""" create a urllib2.Request """
	if data:
		data = urllib.urlencode(data)
	return urllib2.Request(url, data, headers)

def sflyCookie(name, data):
	if type(data) == dict:
		value = ''
		for item in data:
			value += item + ':' + str(data[item]) + '&'
		value = value[:-1]
	else:
		value = data
	
	return  cookielib.Cookie(version=0, name=name, value=value, port=None, port_specified=False, domain='.shutterfly.com', domain_specified=True, domain_initial_dot=True, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={}, rfc2109=False)

###############################################################################
# Shutterfly exception processor
###############################################################################
class ShutterflyException(Exception):
	"""
	Web exception
	"""
	pass

def encode_multipart_formdata(fields, files):
	"""
	fields is a sequence of (name, value) elements for regular form fields.
	files is a sequence of (name, filename, value) elements for data to be uploaded as files
	Return (content_type, body) ready for httplib.HTTP instance
	"""
	#mimetools._prefix = "some-random-string-you-like"    # vincent patch : http://mail.python.org/pipermail/python-list/2006-December/420360.html
	BOUNDARY = "END_OF_PART" #mimetools.choose_boundary()
	CRLF = '\r\n'
	L = []
	for (key, value) in fields:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"' % key)
		L.append('')
		L.append(value)
	for (filename, mimeType, value) in files:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="Image.Data"; filename="%s"' % (filename))
		L.append('Content-Type: %s' % mimeType)
		L.append('')
		L.append(value)
	L.append('--' + BOUNDARY + '--')
	L.append('')
	body = CRLF.join(L)
	
	content_type = 'multipart/form-data; boundary="%s"' % BOUNDARY
	
	return content_type, body

###############################################################################
# Shutterfly error processor
###############################################################################
class ShutterflyHTTPErrorProcessor(urllib2.HTTPErrorProcessor):
	def http_response(self, request, response):
		return urllib2.HTTPErrorProcessor.http_response(self, request, response)
	
	https_response = http_response

###############################################################################
# Shutterfly api (URL encoder)
###############################################################################
class SFApi:
	accounturl = "http://www.shutterfly.com/account/acc_info.jsp"
	entryurl = "http://www.shutterfly.com/signin/viewSignin.sfly"
	loginurl = "https://www.shutterfly.com/signin/signin.sfly"
	albumurl = "http://www.shutterfly.com/action/lightbox/server?action=aCount,aPage&pageNumber=%(page)s&activeAlbumIdx=0&ft=1&mode=albums&view=albums&singleSelect=false&ts=0&sscf=1"
	addalbumurl = "http://www.shutterfly.com/view/album_create.jsp"
	photourl = "http://www.shutterfly.com/action/lightbox/server?action=pFrame,pView,pCount,pPage&albumId=%(albumid)s&pageNumber=%(page)s&pictureSrc=A&ft=1&mode=pictures&view=small&singleSelect=false&ts=0&sscf=1"
	delphotourl = "http://www.shutterfly.com/action/lightbox/server?action=deletePictures,pCount,pPage&albumId=%(albumid)s&pageNumber=%(page)s&pictureSrc=A&ft=1&mode=pictures&view=small&singleSelect=false&ts=0&sscf=1"
	uploadurl = "http://www.shutterfly.com/add/upload_browse.jsp"
	uploadimageurl = "http://up1.shutterfly.com/UploadImage"

	def _getaccounturl():
		return SFApi.accounturl
	
	def _getentryurl():
		return SFApi.entryurl
	
	def _getloginurl():
		return SFApi.loginurl
	
	def _getalbumurlbypage(page):
		return SFApi.albumurl % {"page" : page}
	
	def _getaddalbumurl():
		return SFApi.addalbumurl
	
	def _getphotourlbyid(aid, page):
		return SFApi.photourl % {"albumid" : aid, "page" : page}

	def _getdelphotourlbyid(aid, page):
		return SFApi.delphotourl % {"albumid" : aid, "page" : page}
	
	def _getuploadurl():
		return SFApi.uploadurl
	
	def _getuploadimageurl():
		return SFApi.uploadimageurl
	
	getaccounturl = staticmethod(_getaccounturl)
	getentryurl = staticmethod(_getentryurl)
	getloginurl = staticmethod(_getloginurl)
	getalbumurlbypage = staticmethod(_getalbumurlbypage)
	getaddalbumurl = staticmethod(_getaddalbumurl)
	getphotourlbyid = staticmethod(_getphotourlbyid)
	getdelphotourlbyid = staticmethod(_getdelphotourlbyid)
	getuploadurl = staticmethod(_getuploadurl)
	getuploadimageurl = staticmethod(_getuploadimageurl)

###############################################################################
# Shutterfly Response Handler
###############################################################################
class ShutterflyCookieProcessor(urllib2.HTTPCookieProcessor, urllib2.HTTPRedirectHandler):
	"""
	Kill form header stuff on a 302 redirect, getting rid of just content-length 
	does not appear to help. Maybe just need to delete content-type but for now
	I delete the whole header, meh.
	Bug: 1401 - http://bugs.python.org/issue1401 
	"""
	def http_error_302(self, req, fp, code, msg, headers):
		for key in req.headers.keys():
			if key.lower() == 'content-length':
				req.headers = {}
		result = urllib2.HTTPRedirectHandler.http_error_301(
			self, req, fp, code, msg, headers)
		return result

###############################################################################
# Shutterfly connection object class
###############################################################################
class ShutterflyConnection(object):
	__user = None
	__fid = None
	__cj = None
	__opener = None
	
	user = property(lambda s: s.__user)
	fid = property(lambda s: s.__fid)
	opener = property(lambda s: s.__opener)
	
	def __init__(self, user, password):
		"""
		Check if the user is already connected
		Connect to the shutterly entrance page to aquire a FID from 
		the response url
		Login using credentials and aquired FID
		"""
		self.__cj = cookielib.CookieJar()
		self.__opener = urllib2.build_opener(ShutterflyCookieProcessor(self.__cj))
		urllib2.install_opener(self.opener)

		user = utf8(user)
		password = utf8(password)
		self.__user = user
		
		request = mkRequest(SFApi.getaccounturl())
		response = self.opener.open(request)
		buf = response.read()
		response.close()
		
		if buf.find(user) > 0:
			# Found the specified user logged in.
			return
		
		request = mkRequest(SFApi.getentryurl())
		response = self.opener.open(request)
		self.__fid = parse_qs(urlparse(response.geturl())[4])['fid'][0]
		
		headers = {"Content-type" : "application/x-www-form-urlencoded", }
		data =    {"userName" : user, 
		           "password" : password, 
		           "_rememberUserName" : "off", 
		           "fid" : self.__fid, }
		
		request = mkRequest(SFApi.getloginurl(), data, headers)
		response = self.opener.open(request)
		buf = response.read()
		response.close()
		
		if buf.find("return.sfly") == -1:
			raise ShutterflyException("Unable to connect (wrong credentials?)")
	
	def getfid(self):
		return self.fid
	
	def setCookie(self, cookie):
		self.__cj.set_cookie(cookie)

###############################################################################
# Shutterfly api
###############################################################################
class Shutterfly:
	def __init__(self, user, password):
		""" Create a Shutterfly instance """
		self.__sc = ShutterflyConnection(user, password)
	
	def getAlbums(self):
		"""
		Get a dictionary of available Shutterfly albums on this account
		"""
		request = mkRequest(SFApi.getalbumurlbypage(1))
		response = self.__sc.opener.open(request)
		buf = response.read()
		response.close()
		
		if buf.find("var status='failure'") > -1:
			raise ShutterflyException("Find albums page not retrieved (url changed?)")
		if buf.find("var status='notLoggedIn'") > -1:
			raise ShutterflyException("No longer logged in (timeout, logged in elsewhere?)")

		page = 1
		count = int(re.search("totalPics\s*=\s*(\d+)", buf).group(1))
		perpage = int(re.search("picsThisPage\s*=\s*(\d+)", buf).group(1))

		l = {}

		while count > 0:
			details = re.findall("aList\[(\d+)\]='(.*)';\ntList\[\d+\]='(.*)';\ncList\[\d+\]='(.*)';", buf)
			for items in details:
				alb = ShutterflyAlbum(self.__sc, int(items[0]), items[1], items[2], int(items[3]))
				l[alb.name] = alb
			count -= perpage
			page += 1
			if count > 0:
				request = mkRequest(SFApi.getalbumurlbypage(page))
				response = self.__sc.opener.open(request)
				buf = response.read()
				response.close()
		
		return l

	def createAlbum(self, name, description=""):
		"""
		Create an album on Shutterfly and return the ShutterflyAlbum instance
		Need to retrieve AuthID before uploading (adding albums)
		"""
		name = utf8(name)
		
		headers = {"Content-type" : "application/x-www-form-urlencoded", }
		data =    {"albumTitle" : name, 
		           "albumDesc" : description, 
		           "createAlbum" : "1", }
		
		request = mkRequest(SFApi.getaddalbumurl(), data, headers)
		response = self.__sc.opener.open(request)
		buf = response.read()
		response.close()
		
		albums = self.getAlbums()
		return albums[name]

###############################################################################
# Shutterfly album object
###############################################################################
class ShutterflyAlbum(object):
	__sc = None
	__index = None
	__id = None
	__name = None
	__length = None
	
	index = property(lambda s: s.__index)
	id = property(lambda s: s.__id)
	name = property(lambda s: s.__name)
	length = property(lambda s:  s.__length)
	
	def __init__(self, sc, index, id, name, length):
		""" Should only be called by Shutterfly """
		self.__sc = sc
		self.__index = index
		self.__id = utf8(id)
		self.__name = name
		self.__length = length
	
	def getPhotos(self):
		"""
		Get a dictionary of available photos in this album
		"""
		request = mkRequest(SFApi.getphotourlbyid(self.__id, 1))
		response = self.__sc.opener.open(request)
		buf = response.read()
		response.close()
		
		if buf.find("var status='failure'") > -1:
			raise ShutterflyException("List photos page not retrieved (url changed?)")
		if buf.find("var status='notLoggedIn'") > -1:
			raise ShutterflyException("No longer logged in (timeout, logged in elsewhere?)")

		page = 1
		count = int(re.search("totalPics\s*=\s*(\d+)", buf).group(1))
		perpage = int(re.search("picsThisPage\s*=\s*(\d+)", buf).group(1))
		
		l = {}
		
		while count > 0:
			details = re.findall("pList\[(\d+)\]='(.*)';\ntList\[\d+\]='(.*)';", buf)
			for items in details:
				photo = ShutterflyPhoto(int(items[0]), page-1, items[1], items[2])
				l[photo.id] = photo
			count -= perpage
			page += 1
			if count > 0:
				request = mkRequest(SFApi.getphotourlbyid(self.__id, page))
				response = self.__sc.opener.open(request)
				buf = response.read()
				response.close()
		
		return l
	
	def uploadPhoto(self, filename, mimeType, name, description = ""):
		"""
		Upload a photo to this album
		"""
		filename = utf8(filename)
		
		if os.path.isfile(filename):
			request = mkRequest(SFApi.getuploadurl())
			response = self.__sc.opener.open(request)
			buf = response.read()
			response.close()
			
			data = []
			for item in ['ProtocolVersion', 'RequestType', 'AuthenticationID', 
			             'PartnerID', 'PartnerSubID', 'previewURL', 'redirect', 
			             'doNotDisplayFormAfterUpload']:
				data.append((item, re.search('name="'+item+'" value="(.*)"', buf).group(1)))
			
			data.append(('Image.AlbumID', self.__id))
			data.append(('Image.AlbumName', self.__name))
			data.append(('Image.UploadTime', time.strftime(FORMAT_STRING)))
			
			content_type, body = encode_multipart_formdata(data, 
				[(name, mimeType, open(filename, "rb").read())])
			
			headers = {"Content-Type" : content_type, 
			           "Content-Length" : str(len(body)), }
			
			request = urllib2.Request(SFApi.getuploadimageurl(), 
			                          body, headers)
			response = self.__sc.opener.open(request)
			buf = response.read()
			response.close()
			
			if response.geturl().find("Success=1") == -1:
				raise ShutterflyException("Could not add photo")
			
			photoid = re.search('name="vcidList" value="(.*)"', buf).group(1)
			# Shutterfly started lying about the photo id.  Need to watch this value
			# Maybe just find the new photo by running another get_all ?
			photoid = photoid[:34] + '2' + photoid[35:]
			self.__length += 1
			return ShutterflyPhoto(self.length, 0, photoid, name)
			
		else:
			raise ShutterflyException("File does not exist")
	
	def deletePhoto(self, photo):
		cdata = {'mode' : 'pictures',
					'album' : self.index,
					'view' : 'small',
					'name' : self.id,
					'selected' : photo.index + PERPAGE * photo.page,
					'albPg' : 0,
					'qty' : self.length,
					'fso' : 201,
					'pView' : 'small',
					'pg' : photo.page,
					'selSet' : '1'}
		cookie = sflyCookie('sflyImg', cdata)
		self.__sc.setCookie(cookie)

		request = urllib2.Request(SFApi.getdelphotourlbyid(self.id, 1))
		response = self.__sc.opener.open(request)
		buf = response.read()
		response.close()
		
		if buf.find("failure") > -1:
			raise ShutterflyException("Did not successfully delete photo")
		
		
			
	def __repr__(self):
		return "<album %s : %s>" % (self.__id, self.__name)

class ShutterflyPhoto(object):
	__index = None
	__page = None
	__id = None
	__url = None
	__title = None
	
	index = property(lambda s: s.__index)
	page = property(lambda s: s.__page)
	id = property(lambda s: s.__id)
	url = property(lambda s: s.__url)
	title = property(lambda s: s.__title)
	
	def __init__(self, index, page, id, title):
		self.__index = index					# monotonically incrementing index (unique to page)
		self.__page = page					# album page for photo
		self.__id = utf8(id)					# unique photo id
		self.__url = "http://im1.shutterfly.com/procserv/" + id[:35] + '7' + id[36:]
		self.__title = title					# photo title

