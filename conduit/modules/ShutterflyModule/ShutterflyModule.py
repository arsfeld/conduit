"""
Shutterfly Data Sink
"""
import conduit
from conduit import log, logd, logw
import conduit.Utils as Utils
from conduit.datatypes import Rid
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions

Utils.dataprovider_add_dir_to_path(__file__, "shutterfly")
from shutterfly import Shutterfly

MODULES = {
	"ShutterflySink" : {"type" : "dataprovider"}
}

class ShutterflySink(Image.ImageSink):
	
	_name_ = "Shutterfly"
	_description_ = "Sync Your Shutterfly Photos"
	_module_type_ = "sink"
	_icon_ = "shutterfly"
	
	def __init__(self, *args):
		Image.ImageSink.__init__(self)
		self.need_configuration(True)
		
		self.username = ""
		self.password = ""
		self.album = ""
		
		self.sapi = None
		self.salbum = None
		self.sphotos = None
	
	def _get_photo_info(self, id):
		if self.sphotos.has_key(id):
			return self.sphotos[id]
		else:
			return None
	
	def _get_photo_formats(self):
		return ("image/jpeg", )
	
	def refresh(self):
		Image.ImageSink.refresh(self)
		self.sapi = Shutterfly(self.username, self.password)
		
		albums = self.sapi.getAlbums()
		if not albums.has_key(self.album):
			self.salbum = self.sapi.createAlbum(self.album)
		else:
			self.salbum = albums[self.album]
		
		self.sphotos = self.salbum.getPhotos()
	
	def get_all(self):
		return self.sphotos.keys()
	
	def delete(self, LUID):
		"""
		Delete a photo by ID
		"""
		if not self.sphotos.has_key(LUID):
			logw("Photo does not exist")
			return
		
		# Need to figure out how to delete a photo (javascript hell)
		#self.salbum.deletePhoto(self.sphotos[LUID])
		del self.sphotos[LUID]
	
	def _upload_photo(self, uploadInfo):
		"""
		Upload to album
		"""
		try:
			ret = self.salbum.uploadPhoto(uploadInfo.url, uploadInfo.mimeType, uploadInfo.name)
			return Rid(ret.id)
		except Exception, e:
			raise Exceptions.SyncronizeError("Shutterfly Upload Error.")
	
	def configure(self, window):
		"""
		Configures the ShutterflySink
		"""
		widget = Utils.dataprovider_glade_get_widget(
			__file__,
			"shutterfly.glade",
			"ShutterflySinkConfigDialog")
		
		# Get configuration widgets
		username = widget.get_widget("username")
		password = widget.get_widget("password")
		album = widget.get_widget("album")
		
		# Load the widgets with presets
		username.set_text(self.username)
		password.set_text(self.password)
		album.set_text(self.album)
		
		dlg = widget.get_widget("ShutterflySinkConfigDialog")
		
		response = Utils.run_dialog(dlg, window)
		
		if response == True:
			self.username = username.get_text()
			self.password = password.get_text()
			self.album = album.get_text()
			
			self.set_configured(self.is_configured())
		
		dlg.destroy()
	
	def get_configuration(self):
		return {
			"username" : self.username, 
			"password" : self.password, 
			"album" : self.album
			}
	
	def is_configured(self):
		if len(self.username) < 1:
			return False
		
		if len(self.password) < 1:
			return False
		
		if len(self.album) < 1:
			return False
		
		return True
	
	def get_UID(self):
		return self.username

