using System;
using NDesk.DBus;
namespace Conduit {
 	[Interface("org.conduit.Application")]
	internal interface IApplication {

	 	ObjectPath BuildConduit (ObjectPath source, ObjectPath sink);

	 	ObjectPath BuildConduit (string key);

		string[] GetAllDataProviders (); 

		ObjectPath GetDataProvider (string key);

		ObjectPath NewSyncSet ();

		void Quit ();
	}

	public class Application {
		private IApplication dbus_application = null;

		public Application() {
			if (!Bus.Session.NameHasOwner(Util.APPLICATION_BUSNAME))
				throw new Exception("Conduit is not available.");
			
	        dbus_application = Util.GetObject<IApplication> (new ObjectPath ("/"));
		}

		public Conduit BuildConduit (DataProvider source, DataProvider sink) {
			ObjectPath path = dbus_application.BuildConduit (source.Path, sink.Path); 
			return new Conduit (path);
		}

		public string[] GetAllDataProviders () {
			return dbus_application.GetAllDataProviders (); 
		}

		public DataProvider GetDataProvider (string key) {
			ObjectPath path = dbus_application.GetDataProvider (key); 
			return new DataProvider (path);
		}

	}
}
