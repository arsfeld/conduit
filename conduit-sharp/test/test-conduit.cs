using System;
using System.Collections.Generic;
using Conduit;

using NDesk.DBus;

public class Program {
	public static void Main () {
		BusG.Init ();
		Gtk.Application.Init ();
		
		Conduit.Application app = new Conduit.Application ();

		DataProvider source = app.GetDataProvider ("TestFolderTwoWay");
		DataProvider sink   = app.GetDataProvider ("TestFolderTwoWay");

		Conduit.Conduit conduit = app.BuildConduit (source, sink);
		SyncSet.Gui.AddConduit (conduit);

		conduit.SyncStarted += HandleSyncStarted;
		conduit.SyncProgress += HandleSyncProgress;
		conduit.SyncCompleted += HandleSyncCompleted;

		Console.WriteLine ("Now Synchronise the Conduit...");

		// mainloop, for events processing
		Gtk.Application.Run ();
	}

	private static void HandleSyncStarted () {
		Console.WriteLine ("Sync Started");
	}
	private static void HandleSyncProgress (double progress) {
		Console.WriteLine ("Sync Progress");
	}
	private static void HandleSyncCompleted (bool aborted, bool error, bool conflict) {
		Console.WriteLine ("Sync Completed");
		Gtk.Application.Quit ();
	}
}

