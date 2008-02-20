using System;
using System.Collections.Generic;
using Conduit;


public class Program {
	public static void Main() {
		Application app = new Conduit.Application();
		DataProvider dp = app.GetDataProvider ("FolderTwoWay");
		
		foreach (KeyValuePair<string, string> keyPair in dp.GetInformation())
			Console.WriteLine("{0} {1}", keyPair.Key, keyPair.Value);
		
		Console.WriteLine("Configured: {0}", dp.IsConfigured(true, true));
	}
}
