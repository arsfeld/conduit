"""
Copyright (c) 2006 Peter Moberg <moberg.peter@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

On Debian systems, the complete text of the GNU General Public
License can be found in /usr/share/common-licenses/GPL file.
"""

import os
import tempfile
import tarfile
import gtk
import config
import gconf_import
import ConfigParser

class Layouts:
	""" This class represent all avaible layouts. """
	__data = {}	
	__names = []
	#def __init__(self,addFunction=None):
#		self.load(addFunction)

	def load(self,addFunction=None):
		""" Loads info and screenshots for all layout files """
		#if not os.path.exists(config.defaultLayoutDir):
		#	os.mkdir(config.defaultLayoutDir)
		#	raise RuntimeError, "Error: '" + config.defaultLayoutDir + "' does not exist"
		#	return 

		layoutDirs = config.defaultLayoutDirs
		for dir in layoutDirs:
			if os.path.exists(dir):
				files = os.listdir(dir)
				for file in files:
					#print "Loading file: "+ file
					try:
						filePath = dir + file
						if os.path.isfile(filePath):
							if tarfile.is_tarfile(filePath):
								print "Loading: " + filePath
								layout = Layout(dir, file)
								self.__data[layout.name] = layout
								self.__names.append(layout.name)
								
								if addFunction != None:
									addFunction(layout)
					except Exception, e:
						print "Error loading layout file: " + file
						print e
	
	def add(self, layout):
		self.__data[layout.name] = layout
		self.__names.append(layout.name)	
	
	def append(self, file):
		layoutDirs = config.defaultLayoutDirs
		for dir in layoutDirs:
			try:
				filePath = dir + file
				if os.path.isfile(filePath):
					if tarfile.is_tarfile(filePath):
						#print "Loading: " + filePath
						layout = Layout(dir, file)
						#print layout
						self.__data[layout.name] = layout
						self.__names.append(layout.name)
						return layout.name
			except Exception, e:
				print "Error loading layout file: " + file
				print e
		
	def clear(self):
		""" Unload all layouts """
		self.__data = {}
		self.__names = []
	
	def reload(self):
		""" Reloads all layouts """
		self.clear()
		self.load()
	
	def getLayout(self,name):
		""" Returns the layout with name 'name' """
		return self.__data[name]

	def getLayoutNames(self):
		""" Returns a list containing the names of all loaded layouts, usefull to build the layout list in the GUI """
		return self.__names

	def setLayout(self, name):
		""" Imports layout with name 'name' into GConf and configures launchers """
		import shutil

		launchersPath = self.__data[name].getLaunchers()
		for file in os.listdir(launchersPath):
			#print "launcher: " + file 
			shutil.move(launchersPath + "/" + file, config.defaultLauncherPath + "/" + file)
		os.rmdir(launchersPath)

		importer = gconf_import.GConfImport()
		xml = self.__data[name].getPanel()
		importer.importXml(xml)
		
		# Not a very nice solution... 
		os.system("killall gnome-panel")

class Layout:
	""" The Layout represents a layout. Layout data are loaded from file """
	name = ""
	description = ""
	gnomeVersion = ""
	file = ""
	dir = ""
	__panel = ""
	__preview = None

	def __init__(self, dir, file):
		self.dir = dir
		self.file = file
		self.__load()


	def getPanel(self):
		""" Returns the XML for the panel """
		if (self.__panel == "" or self.__panel == None):
			filePath = self.dir + self.file
			if tarfile.is_tarfile(filePath):
				tar = tarfile.open(filePath, "r")
				self.__panel = "".join( tar.extractfile( tar.getmember( "panel.xml" )).readlines() )
		return self.__panel
		

	def getLaunchers(self):
		""" Returns a path to where the lauchers are extracted """
		tmpDir = tempfile.mkdtemp()
		returnDir = tempfile.mkdtemp()

		filePath = self.dir + self.file
		if 0: #tarfile.is_tarfile(filePath):
			if tarfile.is_tarfile(filePath):
				tar = tarfile.open(filePath, "r")
				tar.extract(tar.getmember("launchers.tar"), tmpDir)

				launchersTar = tarfile.open(tmpDir + '/launchers.tar', "r")
				for launcher in launchersTar.getmembers():	
					launchersTar.extract(launcher,returnDir) 
				os.remove(tmpDir + "/launchers.tar")
				os.rmdir(tmpDir)
		print returnDir
		return returnDir


	def getPreview(self):
		""" Return reference to the preview """
		return self.__preview


	def __load(self):
		""" Load layout data from disk """
		#if not os.path.exists(config.defaultLayoutDir):
		#	raise RuntimeError, "Error: '" + config.defaultLayoutDir + "' does not exist"
		#	return 

		#print "Loading layouts"
		filePath = self.dir + self.file
		if tarfile.is_tarfile(filePath):
			rawImage = None
			info = ""
			tar = tarfile.open(filePath, "r")

			for tarinfo in tar:
				if tarinfo.isreg():
					if (tarinfo.name == "info.ini"):
						info = "".join(tar.extractfile(tarinfo).readlines())
					elif (tarinfo.name == "preview.png"):
						rawImage = tar.extractfile(tarinfo).read()
			tar.close()

			(self.name, self.description, self.gnomeVersion) = self.__parseInformation(info)
			if (rawImage != None):
				self.__preview = gtk.gdk.PixbufLoader();
				self.__preview.write(rawImage); 
				self.__preview.close(); 


	def __parseInformation(self,info):
		#print "Parsing information..."
		""" Parses the information stored in info.ini """
		#xmldoc = minidom.parseString( infoXml )
		#name = xmldoc.getElementsByTagName('name')[0].firstChild.data
			
		#descXml = xmldoc.getElementsByTagName('description')
		#if descXml[0].firstChild != None:
			#description = descXml[0].firstChild.data
		#else:
			#description = ""

		#gnomeXml = xmldoc.getElementsByTagName('gnomeversion')
		#if gnomeXml[0].firstChild != None :
			#gnomeVersion = gnomeXml[0].firstChild.data
		#else:
			#gnomeVersion = ""
		#print "info:"
		#print info
		#print "---"
		cp = ConfigParser.ConfigParser()
		try:
			# ConfigParser should really be able to parse strings, but it can not.
			tmp = tempfile.NamedTemporaryFile()
			tmp.write(info)
			tmp.flush()
	
			cp = ConfigParser.ConfigParser()
			cp.read(tmp.name)
			
			import sys
			#print "CP:"
			#cp.write(sys.stdout)
			#print "---"
			
			name = cp.get("layout", "name")
			description = cp.get("layout", "description")
			gnomeVersion = cp.get("layout", "gnomeversion")
			#print (name,description,gnomeVersion)
			return (name,description,gnomeVersion)
		except Exception, e:
			print "ERROR: info.ini is not valid"
			print e
			return
