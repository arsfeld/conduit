using System;
using System.Collections.Generic; 
using NDesk.DBus;

namespace Conduit {
 	[Interface("org.conduit.DataProvider")]
	internal interface IDataProvider {

		bool AddData (string Uri);

		void Configure ();

		string GetConfigurationXml ();

		IDictionary<string, string> GetInformation ();

		bool IsConfigured (bool isSource, bool isTwoWay);

		bool IsPending ();

		void SetConfigurationXml (string xml);
	}

	public class DataProvider {
	 	private IDataProvider dbus_dataprovider = null;
		private ObjectPath path;

		internal ObjectPath Path {
		 	get { return path; }
		}

		internal DataProvider (ObjectPath path) {
			dbus_dataprovider = Util.GetObject<IDataProvider> (path); 
			this.path = path;
		}

		public void Configure () {
			dbus_dataprovider.Configure (); 
		}

		public bool AddData (string uri) {
			return dbus_dataprovider.AddData (uri); 
		}

		public string GetConfigurationXml () {
			return dbus_dataprovider.GetConfigurationXml (); 
		}

		public IDictionary<string, string> GetInformation () {
			return dbus_dataprovider.GetInformation (); 
		}

		public bool IsConfigured (bool isSource, bool isTwoWay) {
			return dbus_dataprovider.IsConfigured (isSource, isTwoWay); 
		}

		public bool IsPending () {
			return dbus_dataprovider.IsPending (); 
		}

		public void SetConfigurationXml (string xml) {
			dbus_dataprovider.SetConfigurationXml (xml); 
		}
	} 
}
