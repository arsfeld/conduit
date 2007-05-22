# Most of the code from this file comes from:
#
# Copyright (C) 2004 John C. Ruttenberg
#
# with some small additions by
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

import string
import re
from xmlrpclib import *
import httplib, mimetypes
from xml.etree.ElementTree import fromstring, ElementTree 

import os
from os import path

version = "1.10"

def error(string):
	from sys import exit, stderr
	stderr.write(string + "\n")
	exit(1)

def message(opts,string):
	from sys import stderr
	if not opts.quiet:
		stderr.write(string)

def minutes_seconds(seconds):
    if seconds < 60:
        return "%d" % seconds
    else:
        return "%d:%02d" % (seconds / 60, seconds % 60)
	

def filename_get_data(name):
	f = file(name,"rb")
	d = f.read()
	f.close()
	return d
	
def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'	

class SmugMug:
	def __init__(self,account,passwd):
		self.account = account
		self.password = passwd
		self.sp = ServerProxy("https://upload.smugmug.com/xmlrpc/")
		self.api_version = "1.0"
		self.categories = None
		self.subcategories = None
		self.albums = None
		self.login()

	def __del__(self):
		self.logout()

	def login(self):
		rep = self.sp.loginWithPassword(self.account,self.password,self.api_version)
		self.session = rep['SessionID']

	def logout(self):
		self.sp.logout(self.session)
		
	def create_album(self,name,category_id=0):
		return self.sp.createAlbum(self.session,name,category_id)

	def get_categories(self):
		categories = self.sp.getCategories(self.session)
		self.categories = {}
		for category in categories:
			self.categories[category['Title']] = category['CategoryID']
			
	def get_category(self,category_string):
		if re.match("\d+$",category_string):
			return string.atoi(category_string)
		if not self.categories:
			self.get_categories()

		if not self.categories.has_key(category_string):
			error("Unknown category " + category_string)
		else:
			return self.categories[category_string]

	def get_subcategory(self,category,subcategory_string):
		if re.match("\d+$",subcategory_string):
			return string.atoi(subcategory_string)
		if not self.subcategories:
			self.subcategories = {}
		if not self.subcategories.has_key(category):
			subcategories = self.sp.getSubCategories(self.session,category)
			subcategory_map = {}
			for subcategory in subcategories:
				subcategory_map[subcategory['Title']] = subcategory['SubCategoryID']
			self.subcategories[category] = subcategory_map

		if not self.subcategories[category].has_key(subcategory_string):
			error("Unknown subcategory " + subcategory_string)
		else:
			return self.subcategories[category][subcategory_string]
			
	def get_albums (self):
		albums = self.sp.getAlbums (self.session)
		self.albums = {}
		for album in albums:
			self.albums[album['Title']] = album['AlbumID']
			
		return self.albums
			
	def get_images (self, albumID):
		return self.sp.getImages (self.session, albumID)
			
	def get_image_info (self, imageID):
		try:
			return self.sp.getImageInfo (self.session, imageID)
		except:
			return None		

	def upload_files(self,albumid,opts,args,local_information=None):
		from time import time
		from os import stat
		from string import atoi

		max_size = atoi(opts.max_size)

		total_size = 0
		sizes = {}
		files = []
		for file in args:
			if not path.isfile(file):
				message(opts,"%s not a file.	Not uploading\n")
				continue
			size = stat(file).st_size
			if size > max_size:
				message(opts,"%s size %d greater than %d.	Not uploading\n" %
								(file,size,max_size))
			else:
				files.append(file)
				sizes[file] = size
				total_size += size

		t = time()
		total_xfered_bytes = 0

		for file in files:
			t0 = time()
			message(opts,file + "...")
			if not opts.test:
				self.upload_file(albumid,file,caption(file,opts))
			t1 = time()
			if local_information:
				local_information.file_uploaded(file)
			seconds = t1 - t0
			try:
				bytes_per_second = sizes[file] / seconds
				total_xfered_bytes += sizes[file]
				estimated_remaining_seconds = (total_size - total_xfered_bytes) / bytes_per_second
				message(opts,"[OK] %d bytes %d seconds %dKB/sec ETA %s\n" % (
					sizes[file],
					seconds,
					bytes_per_second / 1000,
					minutes_seconds(estimated_remaining_seconds)))
			except:
				pass			

		total_seconds = time() - t
		try:
			message(opts,"%s %d bytes %dKB/sec\n" % (
				minutes_seconds(total_seconds),
				total_size,
				(total_size / total_seconds) / 1000))
		except:
			pass

	def upload_file(self,albumid,filename,caption=None):
		fields = []
		fields.append(['AlbumID',str(albumid)])
		fields.append(['SessionID',self.session])
		if caption:
			fields.append(['Caption',caption])

		data = filename_get_data(filename)
		fields.append(['ByteCount',str(len(data))])

		file = ['Image',filename,data]
		rsp = self.post_multipart("upload.smugmug.com","/photos/xmladd.mg",fields,[file])

		try:
			tree = ElementTree(fromstring(rsp))
			return tree.find("//int").text
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
		
