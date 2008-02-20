using System;
using System.Collections.Generic;

using NDesk.DBus;

namespace Conduit {
 	[Interface("org.conduit.Exporter")]
	internal interface IExporter {
		bool AddData (string uri);
		
		void SinkConfigure();
		
		string SinkGetConfigurationXml ();

		void SinkSetConfigurationXml (string xml);

		IDictionary<string, string> SinkGetInformation ();
	} 

	public class Exporter {
	 	private IExporter exporter_proxy;
		private ObjectPath path;

		internal Exporter (ObjectPath path) {
			this.exporter_proxy = Util.GetObject<IExporter> (path);
			this.path = path;
		}

		public bool AddData (string uri) {
			return exporter_proxy.AddData (uri);
		}

		public void Configure () {
			exporter_proxy.SinkConfigure (); 
		}

		public string GetConfigurationXml () {
			return exporter_proxy.SinkGetConfigurationXml (); 
		}

		public void SinkSetConfigurationXml (string xml) {
			exporter_proxy.SinkSetConfigurationXml (xml); 
		}

		public IDictionary<string, string> GetInformation () {
			return exporter_proxy.SinkGetInformation (); 
		}
	}
}
