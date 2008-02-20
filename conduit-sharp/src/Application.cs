using System;
using NDesk.DBus;

namespace Conduit {
 	[Interface("org.conduit.Application")]
	internal interface IApplication  {

	 	ObjectPath BuildConduit (ObjectPath source, ObjectPath sink);

	 	ObjectPath BuildExporter (string key);

		string[] GetAllDataProviders (); 

		ObjectPath GetDataProvider (string key);

		ObjectPath NewSyncSet ();

		void Quit ();

		event KeyCallBack DataproviderAvailable;

		event KeyCallBack DataproviderUnavailable;
	}

	public class Application {
		public event KeyCallBack DataProviderAvailable;
		public event KeyCallBack DataProviderUnavailable;

		private IApplication application_proxy = null;

		public Application() {
			if (!Bus.Session.NameHasOwner(Util.APPLICATION_BUSNAME))
				throw new Exception("Conduit is not available.");
		
			// get proxy	
			application_proxy = Util.GetObject<IApplication> (new ObjectPath ("/"));

			// connect to events to raise our own
			application_proxy.DataproviderAvailable += HandleDataProviderAvailable;
			application_proxy.DataproviderUnavailable += HandleDataProviderUnavailable;
		}

		public Conduit BuildConduit (DataProvider source, DataProvider sink) {
			ObjectPath path = application_proxy.BuildConduit (source.Path, sink.Path); 
			return new Conduit (path);
		}

		public Exporter BuildExporter (string key) {
		 	ObjectPath path = application_proxy.BuildExporter (key);
			return new Exporter (path);
		}

		public string[] GetAllDataProviders () {
			return application_proxy.GetAllDataProviders (); 
		}

		public DataProvider GetDataProvider (string key) {
			ObjectPath path = application_proxy.GetDataProvider (key); 
			return new DataProvider (path);
		}
		
		// Proxy event handlers

		private void HandleDataProviderAvailable (string key) {
			if (DataProviderAvailable != null)
			 	DataProviderAvailable (key); 
		}

		private void HandleDataProviderUnavailable (string key) {
			if (DataProviderUnavailable != null)
			 	DataProviderUnavailable (key); 
		}
	}
}
