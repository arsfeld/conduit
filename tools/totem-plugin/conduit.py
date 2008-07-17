import os
import totem
import gtk
import dbus, dbus.glib

"""Based on John Stowers' plugin for EOG to upload images to Flickr via Conduit."""

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

MENU_PATH="/tmw-menubar/movie/properties"

SUPPORTED_SINKS = {
	"YouTubeTwoWay" : "Upload to YouTube",
#	"TestVideoSink" : "Test"
}

ICON_SIZE = 24

CONFIG_PATH='~/.conduit/totem-plugin'

NAME_IDX=0
URI_IDX=1
STATUS_IDX=2

class ConduitWrapper:
	def __init__ (self, conduit, name, store):
		self.conduit = conduit
		self.name = name
		self.store = store
		self.rowref = None
		self.configured = False
		self.pendingSync = False

		self.conduit.connect_to_signal ("SyncProgress",
						self._on_sync_progress,
						dbus_interface = CONDUIT_DBUS_IFACE)
		self.conduit.connect_to_signal ("SyncCompleted",
						self._on_sync_completed,
						dbus_interface = CONDUIT_DBUS_IFACE)
		self.conduit.connect_to_signal ("SyncStarted",
						self._on_sync_started,
						dbus_interface = CONDUIT_DBUS_IFACE)

	def _get_configuration (self):
		"""Gets the latest configuration for a given
		dataprovider"""
		config_path = os.path.expanduser (CONFIG_PATH)

		if not os.path.exists (os.path.join (config_path, self.name)):
			return

		f = open (os.path.join (config_path, self.name), 'r')
		xml = f.read ()
		f.close()

		return xml

	def _save_configuration (self, xml):
		"""Saves the configuration XML from a given dataprovider again"""
		config_path = os.path.expanduser (CONFIG_PATH)

		if not os.path.exists (config_path):
			os.mkdir (config_path)

		f = open (os.path.join (config_path, self.name), 'w')
		f.write (xml)
		f.close()

	def _get_rowref (self):
		if self.rowref == None:
			# Store the rowref in the store with the icon Conduit gave us
			info = self.conduit.SinkGetInformation (dbus_interface = EXPORTER_DBUS_IFACE)
			desc = SUPPORTED_SINKS[self.name]
			self.rowref = self.store.append (None,
							 (desc,		#NAME_IDX
							  "",		#URI_IDX
							  "ready"))	#STATUS_IDX
		return self.rowref

	def _configure_reply_handler (self):			
		# Save the configuration
		xml = self.conduit.SinkGetConfigurationXml ()
		self._save_configuration (xml)
		self.configured = True

		# Check if a sync was waiting for the Conduit (sink) to be configured
		if self.pendingSync == True:
			self.pendingSync = False
			self.conduit.Sync (dbus_interface = CONDUIT_DBUS_IFACE)

	def _configure_error_handler (self, error):
		pass

	def _on_sync_started (self):
		self.store.set_value (self._get_rowref(), STATUS_IDX, "uploading")

	def _on_sync_progress (self, progress, uids):
		uris = [str(i) for i in uids]
		delete = []

		treeiter = self.store.iter_children (self._get_rowref ())
		while treeiter:
			if self.store.get_value (treeiter, URI_IDX) in uris:
				delete.append (treeiter)
			treeiter = self.store.iter_next (treeiter)

		for d in delete:
			self.store.remove (d)

		#for uri in uids:
		#	rowref = self._get_rowref_for_photo(str(uri))
		#	print "\t%s - %s" % (uri, rowref)
		#	print "\t",self.photoRefs
		
	def _on_sync_completed (self, abort, error, conflict):
		rowref = self._get_rowref ()
		if abort == False and error == False:
			self.clear ()
			# Update the status
			self.store.set_value (rowref, STATUS_IDX, "finished")
		else:
			# Show the error message in the Conduit GUI
			self.store.set_value (rowref, STATUS_IDX, "error")

	def clear (self):
		rowref = self._get_rowref ()
		# Delete all the videos from the list of videos to upload
		delete = []
		child = self.store.iter_children (rowref)
		while child != None:
			delete.append (child)
			child = self.store.iter_next (child)
		# Need to do in two steps so we don't modify the store while iterating
		for d in delete:
			self.store.remove (d)

	def add_video (self, uri):
		ok = self.conduit.AddData (uri, dbus_interface = EXPORTER_DBUS_IFACE)
		if ok == True:
			# Add to the store
			rowref = self._get_rowref ()
			filename = uri.split ("/")[-1]
			self.store.append (rowref,
					   (filename,	# NAME_IDX
					    uri,	# URI_IDX
					    ""))	# STATUS_IDX

	def sync (self):
		if self.configured == True:
			self.conduit.Sync (dbus_interface = CONDUIT_DBUS_IFACE)
		else:
			# Defer the sync until the Conduit has been configured
			self.pendingSync = True
			# Configure the sink and perform the actual synchronisation
			# when the configuration is finished, this way the Totem GUI doesn't
			# block on the call
			self.conduit.SinkConfigure (reply_handler = self._configure_reply_handler,
						    error_handler = self._configure_error_handler,
						    dbus_interface = EXPORTER_DBUS_IFACE)

class ConduitApplicationWrapper:
	def __init__ (self, startConduit, addToGui):
		self.addToGui = addToGui
		self.app = None
		self.conduits = {}
		# The liststore of videos to be uploaded
		self.store = gtk.TreeStore (str,		#NAME_IDX
					    str,		#URI_IDX
					    str)		#STATUS_IDX

		if startConduit:
			self.start ()
		else:
			obj = self.bus.get_object ('org.freedesktop.DBus', '/org/freedesktop/DBus') 
			dbus_iface = dbus.Interface (obj, 'org.freedesktop.DBus')
			if dbus_iface.NameHasOwner (APPLICATION_DBUS_IFACE):
				self.start ()
			else:
				raise Exception ("Could not connect to Conduit.")
		
	def _build_conduit (self, sinkName):
		if sinkName in self.dps:
			print "Building exporter Conduit %s" % sinkName
			path = self.app.BuildExporter (sinkName)
			exporter = dbus.SessionBus ().get_object (CONDUIT_DBUS_IFACE, path)
			self.conduits[sinkName] = ConduitWrapper (conduit = exporter, name = sinkName, store = self.store)
		else:
			print "Could not build Conduit %s" % sinkName

	def upload (self, name, uri):
		if self.connected ():
			if name not in self.conduits:
				self._build_conduit (name)

			if uri != None:
				# Add the video to the remote Conduit and the liststore
				self.conduits[name].add_video (uri)

	def start (self):
		if not self.connected ():
			try:
				remote_object = dbus.SessionBus ().get_object (APPLICATION_DBUS_IFACE, "/")
				self.app = dbus.Interface (remote_object, APPLICATION_DBUS_IFACE)
				self.dps = self.app.GetAllDataProviders () 
			except dbus.exceptions.DBusException:
				self.app = None
				print "Conduit unavailable"

	def sync (self):
		if self.connected ():
			for c in self.conduits:
				self.conduits[c].sync ()

	def clear (self):
		if self.connected ():
			for c in self.conduits:
				self.conduits[c].clear ()

	def connected (self):
		return self.app != None

class ConduitPlugin (totem.Plugin):
	def __init__ (self):
		self.conduit = ConduitApplicationWrapper (startConduit = True,
							  addToGui = False)

	def _on_upload_clicked (self, action, totem_object):
		current_uri = totem_object.get_current_mrl ()
		name = action.get_property ("name")

		# Add the file to the list and sync it immediately
		self.conduit.upload (name, current_uri)
		self.conduit.sync ()

	def _on_file_opened (self, totem_object, mrl):
		self.top_level_action.set_sensitive (True)

	def _on_file_closed (self, totem_object):
		self.top_level_action.set_sensitive (False)

	def activate (self, totem_object):
		totem_object.connect ("file-opened", self._on_file_opened)
		totem_object.connect ("file-closed", self._on_file_closed)

		ui_action_group = gtk.ActionGroup ("ConduitPluginActions")
		manager = totem_object.get_ui_manager ()

		# Make an action for each sink
		for sink_name in SUPPORTED_SINKS:
			desc = SUPPORTED_SINKS[sink_name]
			action = gtk.Action (name = sink_name,
					     stock_id = "internet",
					     label = desc,
					     tooltip = "")
			action.connect ("activate", self._on_upload_clicked, totem_object)
			ui_action_group.add_action (action)

		# Create a top-level menu
		self.top_level_action = gtk.Action (name = "sync",
						stock_id = "internet",
						label = _("_Share"),
						tooltip = "")
		ui_action_group.add_action (self.top_level_action)

		manager.insert_action_group (ui_action_group, -1)

		mid = manager.new_merge_id ()
		manager.add_ui (merge_id = mid,
				path = MENU_PATH,
				name = "sync",
				action = "sync",
				type = gtk.UI_MANAGER_MENU,
				top = False)

		# Add each action to the menu
		for sink_name in SUPPORTED_SINKS:
			mid = manager.new_merge_id ()
			manager.add_ui (merge_id = mid,
					path = "/tmw-menubar/movie/sync/",
					name = sink_name, 
					action = sink_name,
					type = gtk.UI_MANAGER_MENUITEM, 
					top = False)

		# Make sure the menu starts disabled
		self.top_level_action.set_sensitive (False)

	def deactivate (self, window):
		pass

	def update_ui (self, window):
		pass

	def is_configurable (self):
		return False
