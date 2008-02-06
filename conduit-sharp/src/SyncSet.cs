using System;
using NDesk.DBus;

namespace Conduit {
 	[Interface("org.conduit.SyncSet")]
	internal interface ISyncSet {

		void AddConduit (ObjectPath conduit);

		void DeleteConduit (ObjectPath conduit);

		void RestoreFromXml (string path);

		void SaveToXml (string path);
	}

	public class SyncSet {

		private ObjectPath path;
		private ISyncSet dbus_syncset;

		private static SyncSet gui;
		private static SyncSet dbus;

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
			dbus_syncset = Util.GetObject<ISyncSet> (path);
			this.path = path;
		}

		public void AddConduit (Conduit conduit) {
			dbus_syncset.AddConduit (conduit.Path); 
		}

		public void DeleteConduit (Conduit conduit) {
			dbus_syncset.DeleteConduit (conduit.Path); 
		}

		public void SaveToXml (string path) {
			dbus_syncset.SaveToXml (path);
		}

		public void RestoreFromXml (string path) {
			dbus_syncset.RestoreFromXml (path); 
		}
	}
}
