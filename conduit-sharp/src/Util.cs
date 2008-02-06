using NDesk.DBus;

namespace Conduit {
	internal class Util {
		internal const string APPLICATION_BUSNAME = "org.conduit.Application";

	 	public static T GetObject<T> (ObjectPath path) {
			 return Bus.Session.GetObject<T> (APPLICATION_BUSNAME, path);
		}
	} 
}
