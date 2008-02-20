using System;
using NDesk.DBus;

namespace Conduit {
 	[Interface("org.conduit.SyncSet")]
	internal interface ISyncSet {

		void AddConduit (ObjectPath conduit);

		void DeleteConduit (ObjectPath conduit);

		void RestoreFromXml (string path);

		void SaveToXml (string path);

		event KeyCallBack ConduitAdded;
		event KeyCallBack ConduitRemoved;
	}

	public class SyncSet {

		private ISyncSet syncset_proxy;
		private ObjectPath path;

		private static SyncSet gui;
		private static SyncSet dbus;

		public event KeyCallBack ConduitAdded;
		public event KeyCallBack ConduitRemoved;

		public static SyncSet Gui {
			get {
				if (gui == null) {
					gui = new SyncSet (new ObjectPath ("/syncset/gui"));
				} 
				return gui;
			} 
		}

		public static SyncSet DBus {
		 	get {
				if (dbus == null) {
					dbus = new SyncSet (new ObjectPath ("/syncset/dbus"));
				} 
				return dbus;
			}
		}

		internal ObjectPath Path {
			get { return path; } 
		}

	 	private SyncSet (ObjectPath path) {
			syncset_proxy = Util.GetObject<ISyncSet> (path);
			this.path = path;

			// hookup events
			syncset_proxy.ConduitAdded += HandleConduitAdded;
			syncset_proxy.ConduitRemoved += HandleConduitRemoved;
		}

		public void AddConduit (Conduit conduit) {
			syncset_proxy.AddConduit (conduit.Path); 
		}

		public void DeleteConduit (Conduit conduit) {
			syncset_proxy.DeleteConduit (conduit.Path); 
		}

		public void SaveToXml (string path) {
			syncset_proxy.SaveToXml (path);
		}

		public void RestoreFromXml (string path) {
			syncset_proxy.RestoreFromXml (path); 
		}

		private void HandleConduitAdded (string key) {
			if (ConduitAdded != null)
			 	ConduitAdded (key); 
		}

		private void HandleConduitRemoved (string key) {
			if (ConduitRemoved != null)
			 	ConduitRemoved (key); 
		}
	}
}
