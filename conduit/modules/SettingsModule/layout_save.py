"""
Layout File 
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
import gconf
import gconf_export
import string
import tarfile
import config
import os
import tempfile
import ConfigParser

from gettext import gettext as _

class LayoutSave:
	def __init__(self, name, description, gconfClient = None):
		if (gconfClient == None):
			self.gconfClient = gconf.client_get_default() 
		else:
			self.gconfClient = gconfClient

		# TODO: fetch this
		self.gnomeversion = self.getGnomeVersion()

		self.name = name
		self.description = description
		self.file = ""


	def save(self,file = None, screenshot=True, callback=None):
		if not os.path.exists(config.defaultSaveDir):
			try:
				os.mkdir(config.defaultSaveDir)
			except:
				print _("Error: Could not create directory: ") + config.defaultSaveDir

		if not os.path.exists(config.defaultLauncherPath):
			print _("Error: '%s' does not exist") % config.defaultLauncherPath
			return

		if (file == None):
			self.file = self.name + ".tar.gz"
			"Saveing to : " + config.defaultSaveDir + '/' + self.file
		else:
			self.file = file

		tmpDir = tempfile.mkdtemp()
		gconfExport = gconf_export.GConfExport(self.gconfClient)

		panelFile = open(tmpDir + '/panel.xml','w')
		panelFile.write(gconfExport.export(config.defaultDumpDirs, config.defaultDumpKeys))
		panelFile.close()

		infoFile = open(tmpDir + '/info.ini','w')
		cp = ConfigParser.ConfigParser()
		cp.add_section("layout")
		cp.set("layout", "name", self.name)
		cp.set("layout", "description", self.description)
		cp.set("layout", "gnomeversion", self.gnomeversion)
		#infoFile.write(self.infoTemplate.substitute({'name':self.name,'description':self.description,'gnomeversion':self.gnomeversion}))
		cp.write(infoFile)
		infoFile.close()

		tarFile = tarfile.open(config.defaultSaveDir + self.file,'w:gz')
		tarFile.add(tmpDir + '/panel.xml', "panel.xml")
		tarFile.add(tmpDir + '/info.ini', "info.ini")

		# Add the launchers to the layout file
		layoutsTarFile = tarfile.open(tmpDir + '/launchers.tar','w')
		files = os.listdir(config.defaultLauncherPath)
		for file in files:
			layoutsTarFile.add(config.defaultLauncherPath + "/" + file, file)
		layoutsTarFile.close()
		
		if screenshot:
			import screenshot
			s = screenshot.Screenshot()
			screenshot = s.takeScreenshot(callback=callback)
			
			if (screenshot != "" and screenshot != None):
				tarFile.add(screenshot, "preview.png")

		tarFile.add(tmpDir + '/launchers.tar', "launchers.tar")
		tarFile.close()
		
	def getGnomeVersion(self):
		platform = 0
		minor = 0
		micro = 0
		
		try:
			from xml.dom.minidom import parse
			xmldoc = parse("/usr/share/gnome-about/gnome-version.xml")
			descXml = xmldoc.getElementsByTagName('platform')
			
			if descXml[0].firstChild != None:
				platform = descXml[0].firstChild.data
			
			descXml = xmldoc.getElementsByTagName('minor')
			if descXml[0].firstChild != None:
				minor = descXml[0].firstChild.data
	
			descXml = xmldoc.getElementsByTagName('micro')
			if descXml[0].firstChild != None:
				micro = descXml[0].firstChild.data
		except Exception, e:
			print _("WARNING: could not get gnome version number")
			print e

		return "%s.%s.%s" % (platform, minor, micro)

