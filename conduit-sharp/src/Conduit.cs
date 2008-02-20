using System;
using NDesk.DBus;

namespace Conduit {
	[Interface("org.conduit.Conduit")]
	internal interface IConduit {
		// Methods
		void AddDataProvider (ObjectPath dp, bool trySource);
		
		void DeleteDataProvider (ObjectPath dp);
		
		void DisableTwoWaySync ();
		
		void EnableTwoWaySync ();
		
		bool IsTwoWay ();
		
		void Refresh();
		
		void Sync();
		
		// Events
		event EmptyCallBack SyncStarted;
		
		event EmptyCallBack SyncConflict;
		
		event SyncProgressCallBack SyncProgress;
		
		event SyncCompletedCallBack SyncCompleted;

	}

	public class Conduit {
		private IConduit conduit_proxy;
		private ObjectPath path;
		
		public event EmptyCallBack SyncStarted;
		
		public event EmptyCallBack SyncConflict;
		
		public event SyncProgressCallBack SyncProgress;
		
		public event SyncCompletedCallBack SyncCompleted;

		public ObjectPath Path {
			get { return path; } 
		}

	 	internal Conduit (ObjectPath path) {
	 		conduit_proxy = Util.GetObject<IConduit> (path);
		 	this.path = path;
			
			// hookup events
			conduit_proxy.SyncStarted += HandleSyncStarted;
			conduit_proxy.SyncCompleted += HandleSyncCompleted;		
			conduit_proxy.SyncProgress += HandleSyncProgress;
			conduit_proxy.SyncConflict += HandleSyncConflict;
		}
		
		public void AddDataProvider (DataProvider dp, bool trySource) {
			conduit_proxy.AddDataProvider(dp.Path, trySource);		
		}
		
		public void DeleteDataProvider (DataProvider dp) {
			conduit_proxy.DeleteDataProvider(dp.Path);
		}
		
		public void DisableTwoWaySync () {
			conduit_proxy.DisableTwoWaySync();
		}
		
		public void EnableTwoWaySync () {
			conduit_proxy.EnableTwoWaySync();	
		}
		
		public bool IsTwoWay () {
			return conduit_proxy.IsTwoWay();
		}
		public void Refresh() {
			conduit_proxy.Refresh();
		}
		
		public void Sync() {
			conduit_proxy.Sync();
		}
		
		// Proxy event handlers
		
		private void HandleSyncStarted() {
			if (SyncStarted != null)
				SyncStarted ();
		}
		
		private void HandleSyncConflict () {
			if (SyncConflict != null)
				SyncConflict ();
		}
		
		private void HandleSyncCompleted (bool aborted, bool error, bool conflict) {
			if (SyncCompleted != null)
				SyncCompleted (aborted, error, conflict);
		}
		
		private void HandleSyncProgress (double progress) {
			if (SyncProgress != null)
				SyncProgress (progress);
		}		
	} 
}
