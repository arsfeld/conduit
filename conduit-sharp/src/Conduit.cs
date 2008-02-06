using System;
using NDesk.DBus;

namespace Conduit {
	[Interface("org.conduit.Conduit")]
	internal interface IConduit {
		void AddDataProvider (ObjectPath dp, bool trySource);
		
		void DeleteDataProvider (ObjectPath dp);
		
		void DisableTwoWaySync ();
		
		void EnableTwoWaySync ();
		
		bool IsTwoWay ();
		
		void Refresh();
		
		void Sync();
	}

	public class Conduit {
		private IConduit dbus_conduit;
		private ObjectPath path;

		public ObjectPath Path {
			get { return path; } 
		}

	 	public Conduit (ObjectPath path) {
	 		dbus_conduit = Util.GetObject<IConduit> (path);
		 	this.path = path;
		}
		
		public void AddDataProvider (DataProvider dp, bool trySource) {
			dbus_conduit.AddDataProvider(dp.Path, trySource);		
		}
		
		public void DeleteDataProvider (DataProvider dp) {
			dbus_conduit.DeleteDataProvider(dp.Path);
		}
		
		public void DisableTwoWaySync () {
			dbus_conduit.DisableTwoWaySync();
		}
		
		public void EnableTwoWaySync () {
			dbus_conduit.EnableTwoWaySync();	
		}
		
		public bool IsTwoWay () {
			return dbus_conduit.IsTwoWay();
		}
		public void Refresh() {
			dbus_conduit.Refresh();
		}
		
		public void Sync() {
			dbus_conduit.Sync();
		}
	} 
}
