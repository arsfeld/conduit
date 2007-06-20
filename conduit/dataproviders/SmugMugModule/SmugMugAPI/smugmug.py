# Upload code comes from:
#
# Copyright (C) 2004 John C. Ruttenberg
#
# All other calls re-implemented to use REST api
#
# Copyright (C) 2007 Thomas Van Machelen
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# A copy of the GNU General Public License should be included at the bottom of
# this program text; if not, write to the Free Software Foundation, Inc., 59
# Temple Place, Suite 330, Boston, MA 02111-1307 USA

import httplib, mimetypes
import urllib, urllib2

from xml.dom.minidom import parseString

import os
from os import path

# conduit's api key
API_KEY = "8Od9l5euu0srE81aM0vZlsEHmEFBB9vP"

def get_text(x):
	""" get textual content of the node 'x' """
	r=""
	for i in x.childNodes:
		if i.nodeType == x.TEXT_NODE:
			r+=str(i.nodeValue)
	return r

def get_child(element, name):
	nodes = element.getElementsByTagName(name)

	if len(nodes) > 0:
		return element.getElementsByTagName(name)[0]
	else:
		return None

def get_child_text(element, name):
	return get_text(get_child(element, name))

def get_attribute(element, name):
	if element.hasAttribute(name):
		return str(element.getAttribute(name))
	else:
	 	return None

def filename_get_data(name):
	f = file(name,"rb")
	d = f.read()
	f.close()
	return d

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

class SmugMugException (Exception):
	def __init__ (self, code, message):
		self.code = code
		self.message = message

	def get_printable_error (self):
		return 'Code: %s; Message: %s' % (self.code, self.message)

class SmugMug:
	END_POINT = 'https://api.smugmug.com/hack/rest/1.1.1/?'

	def __init__(self,account,passwd):
		self.account = account
		self.password = passwd

		self.categories = None
		self.subcategories = None
		self.albums = None

		self.login()

	def login(self):
		rsp = self._call_method(method='smugmug.login.withPassword', EmailAddress=self.account, Password=self.password, APIKey=API_KEY)

		self.session = get_child_text(rsp, 'SessionID')

	def logout(self):
		self._call_method(method='smugmug.logout', SessionID=self.session)

	def get_categories(self):
		rsp = self._call_method(method='smugmug.categories.get', SessionID=self.session)

		self.categories = {}

		for cat in rsp.getElementsByTagName('Category'):
			self.categories[get_child_text(cat, 'Title')] = get_attribute(cat, 'id')

		return self.categories

	def create_album(self, name, category=0, is_public=False):
		rsp = self._call_method (method='smugmug.albums.create', SessionID=self.session, Title=name, CategoryID=category, Public=int(is_public))

		return get_attribute(get_child(rsp, 'Album'), 'id')

	def get_albums (self):
		rsp = self._call_method(method='smugmug.albums.get', SessionID=self.session)

		self.albums = {}

		# make an album name: id dict
		for album in rsp.getElementsByTagName('Album'):
			self.albums[get_child_text(album, 'Title')] = get_attribute(album, 'id')

		return self.albums

	def get_images (self, albumID):
		rsp = self._call_method (method='smugmug.images.get', SessionID=self.session, AlbumID=albumID)

		images = []
		
		# create an image id list
		for image in rsp.getElementsByTagName ('Image'):
			images.append (get_attribute(image, 'id'))

		return images

	def get_image_info (self, imageID):
		rsp = self._call_method (method='smugmug.images.getInfo', SessionID=self.session, ImageID=imageID)

		return self._make_dict (rsp.getElementsByTagName('Image')[0])

	def delete_image (self, imageID):
		self._call_method(method='smugmug.images.delete', SessionID=self.session, ImageID=imageID)

	def upload_file(self,albumid,filename,caption=None):
		fields = []
		fields.append(['AlbumID',str(albumid)])
		fields.append(['SessionID',self.session])
		if caption:
			fields.append(['Caption',caption])

		data = filename_get_data(filename)
		fields.append(['ByteCount',str(len(data))])
		fields.append(['ResponseType', 'REST'])

		file = ['Image',filename,data]
		rsp = self.post_multipart("upload.smugmug.com","/photos/xmladd.mg",fields,[file])

		try:
			tree = parseString(rsp).documentElement
			return get_child_text(tree, 'ImageID')
		except:
			return None

	def post_multipart(self,host,selector,fields,files):
		"""
		Post fields and files to an http host as multipart/form-data.	fields is a
		sequence of (name, value) elements for regular form fields.	files is a
		sequence of (name, filename, value) elements for data to be uploaded as
		files Return the server's response page.
		"""
		content_type, body = self.encode_multipart_formdata(fields,files)
		h = httplib.HTTP(host)
		h.putrequest('POST', selector)
		h.putheader('content-type', content_type)
		h.putheader('content-length', str(len(body)))
		h.endheaders()
		h.send(body)
		errcode, errmsg, headers = h.getreply()
		#print errcode
		#print errmsg
		#print headers
		result = h.file.read()
		#print result
		h.close()
		return result

	def encode_multipart_formdata(self,fields,files):
		"""
		fields is a sequence of (name, value) elements for regular form fields.
		files is a sequence of (name, filename, value) elements for data to be
		uploaded as files Return (content_type, body) ready for httplib.HTTP
		instance
		"""
		#print fields
		BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
		CRLF = '\r\n'
		L = []
		for (key, value) in fields:
			L.append('--' + BOUNDARY)
			L.append('Content-Disposition: form-data; name="%s"' % key)
			L.append('')
			L.append(value)
		for (key, filename, value) in files:
			L.append('--' + BOUNDARY)
			L.append('Content-Disposition: form-data; name="%s"; filename="%s"'
							 % (key, filename))
			L.append('Content-Type: %s' % get_content_type(filename))
			L.append("content-length: %d" % (len(value)))
			L.append('')
			L.append(value)
		L.append('--' + BOUNDARY + '--')
		L.append('')
		body = CRLF.join(L)
		content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
		return content_type, body

	def _call_method (self, **args):
		data = urllib.urlencode(args)
		f = urllib2.urlopen(self.END_POINT + data)
		xml = f.read()
		f.close ()
		rsp = parseString(xml).documentElement

		self._check_error(rsp)

		return rsp

	@classmethod
	def _check_error(cls, element):
		if get_attribute(element, 'stat') != 'fail':
		 	return

		err = get_child (element, 'err')
		raise SmugMugException (get_attribute(err, 'code'), get_attribute(err, 'msg'))


	@classmethod
	def _make_dict (cls, element):
		result = {}

		for child in element.childNodes:
			if not child.nodeName:
				continue

			value = get_text(child)
			if not value:
				continue

			result[child.nodeName] = value

		return result

