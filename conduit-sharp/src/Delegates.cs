using System;

namespace Conduit
{
	// General
	public delegate void KeyCallBack (string key);
	public delegate void EmptyCallBack ();
	
	// Conduit
	public delegate void SyncCompletedCallBack (bool aborted, bool error, bool conflict);
	public delegate void SyncProgressCallBack (double progress);
}
