/*
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public
 * License along with main.c; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor Boston, MA 02110-1301,  USA
 */
 
#include <stdio.h>
#include <glib-2.0/glib.h>

#include "conduit-glib/conduit-glib.h"

static void
_dataprovider_available_cb (ConduitGApplication *application, char *hits, gpointer data)
{
    g_print ("Dataprovider %s Available\n", hits);
}

static void
_dataprovider_unavailable_cb (ConduitGApplication *application, char *hits, gpointer data)
{
    g_print ("Dataprovider %s Unavailable\n", hits);
}

static void
_sync_progress_cb (ConduitGConduit *conduit, gdouble progress, gpointer data)
{
	g_print ("Sync (%2.1f%% complete)\n", progress*100.0);
}

static void
_sync_completed_cb (ConduitGConduit *conduit, gboolean a, gboolean e, gboolean c, gpointer data)
{
	g_print ("Sync finished (abort:%u error:%u conflict:%u)\n",a,e,c);
}

static void
_sync_conflict_cb (ConduitGConduit *conduit, gpointer data)
{
	g_print ("Conflict!\n");
}


static void
_print_dataprovider_information(char *key, char *value, gpointer user_data)
{
	if (key && value)
    	g_print ("%s : %s\n", key, value);
}

int
main (int argc, char** argv)
{
    ConduitGApplication     *application;
	ConduitGDataprovider    *source, *sink;
	ConduitGConduit 		*conduit;
	ConduitGSyncset			*gui_syncset;
    GMainLoop               *mainloop;
    gchar 		            **dataproviders;
    
    g_type_init ();
    application = conduit_g_application_new ();
    mainloop = g_main_loop_new (NULL, FALSE);
    
    g_signal_connect (application, "dataprovider-available", (GCallback) _dataprovider_available_cb, NULL);
    g_signal_connect (application, "dataprovider-unavailable", (GCallback) _dataprovider_unavailable_cb, NULL);

    dataproviders = conduit_g_application_get_all_dataproviders(application);
	if (dataproviders) 
	{
		guint		i;
		GHashTable	*info;
		
	    for (i = 0; dataproviders[i] != NULL; i++)
			g_print ("%s\n", dataproviders[i]);
		
		/* Get a datasource */
		source = conduit_g_application_get_dataprovider(application, "TestSource");
		info = conduit_g_dataprovider_get_information(source);
		g_hash_table_foreach (info, (GHFunc)&_print_dataprovider_information, NULL);
		
		/* Get a datasink */
		sink = conduit_g_application_get_dataprovider(application, "TestConflict");
		info = conduit_g_dataprovider_get_information(source);
		g_hash_table_foreach (info, (GHFunc)&_print_dataprovider_information, NULL);

		/* Put them in a conduit */
		conduit = conduit_g_application_build_conduit(application,source,sink);
		g_signal_connect (conduit, "sync-progress", (GCallback) _sync_progress_cb, NULL);
		g_signal_connect (conduit, "sync-completed", (GCallback) _sync_completed_cb, NULL);
		g_signal_connect (conduit, "sync-conflict", (GCallback) _sync_conflict_cb, NULL);
		
		/* Add it to the GUI (optional) */
		gui_syncset = conduit_g_syncset_new(application, "/syncset/gui");
		conduit_g_syncset_add_conduit(gui_syncset, conduit);
		
		conduit_g_conduit_sync(conduit);
	} 
	else 
	{
        g_print ("No dataproviders found");
	}
	
    g_main_loop_run (mainloop);
    
    return 0;
}
