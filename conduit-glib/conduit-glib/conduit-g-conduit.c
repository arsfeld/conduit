/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 4; tab-width: 4 -*- */
/*
 * conduit-glib
 * Copyright (C) John Stowers 2008 <john.stowers@gmail.com>
 * 
 * conduit-glib is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 * 
 * conduit-glib is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public
 * License along with conduit-glib.  If not, write to:
 * 	The Free Software Foundation, Inc.,
 * 	51 Franklin Street, Fifth Floor
 * 	Boston, MA  02110-1301, USA.
 */

#include "conduit-g-conduit.h"
#include "conduit-conduit-bindings.h"
#include "conduit-g-application.h"
#include "conduit-glib-globals.h"
#include "conduit-marshal.h"

struct _ConduitGConduitPrivate {
	ConduitGApplication 	*application;
	DBusGProxy 				*proxy;
	DBusGProxyCall			*proxy_request_call;
};

/* Signals */
enum
{
	SYNC_STARTED,
	SYNC_PROGRESS,
	SYNC_COMPLETED,
	SYNC_CONFLICT,
	
	LAST_SIGNAL
};

static guint g_conduit_signals[LAST_SIGNAL] = { 0 };

/* Private methods */
static void	_dispatch_sync_started					(DBusGProxy 		*proxy,
													 ConduitGConduit 	*conduit);

static void	_dispatch_sync_progress					(DBusGProxy 		*proxy,
													 gdouble			progress,
													 ConduitGConduit 	*conduit);

static void	_dispatch_sync_completed				(DBusGProxy 		*proxy,
													 gboolean			aborted,
													 gboolean			errored,
													 gboolean			conflicted,
													 ConduitGConduit 	*conduit);

static void	_dispatch_sync_conflict					(DBusGProxy 		*proxy,
													 ConduitGConduit 	*conduit);

/* Private methods */

G_DEFINE_TYPE (ConduitGConduit, conduit_g_conduit, G_TYPE_OBJECT);

/**
 * SECTION:conduit-g-conduit
 * @short_description: Represents a conduit
 * @see_also: #ConduitGApplication
 *
 * #ConduitGConduit is a client side representation of a conduit which links one source
 * with one or more dataproviders.
 *
 */

static void
conduit_g_conduit_init (ConduitGConduit *conduit)
{
	ConduitGConduitPrivate *priv;
	
	priv = g_new0 (ConduitGConduitPrivate, 1);
	priv->application = NULL;
	priv->proxy = NULL;
	priv->proxy_request_call = NULL;
	
	conduit->priv = priv;
}

static void
conduit_g_conduit_finalize (GObject *object)
{
	ConduitGConduit 		*conduit;
	ConduitGConduitPrivate *priv;
	
	conduit = CONDUIT_G_CONDUIT(object);
	priv = conduit->priv;
	
	g_object_unref (priv->application);
	
	g_free (conduit->priv);

	G_OBJECT_CLASS (conduit_g_conduit_parent_class)->finalize (object);
}

static void
conduit_g_conduit_class_init (ConduitGConduitClass *klass)
{
	GObjectClass* object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = conduit_g_conduit_finalize;
	
	g_conduit_signals[SYNC_STARTED] =
		g_signal_new ("sync-started",
		              G_OBJECT_CLASS_TYPE (klass),
		              G_SIGNAL_RUN_LAST,
		              0,
		              NULL, NULL,
		              g_cclosure_marshal_VOID__VOID,
		              G_TYPE_NONE, 0);
		              
	g_conduit_signals[SYNC_PROGRESS] =
		g_signal_new ("sync-progress",
		              G_OBJECT_CLASS_TYPE (klass),
		              G_SIGNAL_RUN_LAST,
		              0,
		              NULL, NULL,
		              g_cclosure_marshal_VOID__DOUBLE,
		              G_TYPE_NONE, 1,
		              G_TYPE_DOUBLE);
	
		g_conduit_signals[SYNC_COMPLETED] =
		g_signal_new ("sync-completed",
		              G_OBJECT_CLASS_TYPE (klass),
		              G_SIGNAL_RUN_LAST,
		              0,
		              NULL, NULL,
		              conduit_marshal_VOID__BOOLEAN_BOOLEAN_BOOLEAN,
		              G_TYPE_NONE, 3,
		              G_TYPE_BOOLEAN,G_TYPE_BOOLEAN,G_TYPE_BOOLEAN);
	
	g_conduit_signals[SYNC_CONFLICT] =
		g_signal_new ("sync-conflict",
		              G_OBJECT_CLASS_TYPE (klass),
		              G_SIGNAL_RUN_LAST,
		              0,
		              NULL, NULL,
		              g_cclosure_marshal_VOID__VOID,
		              G_TYPE_NONE, 0);
}

/**
 * conduit_g_conduit_new
 * @application: The session to be parent of the new conduit
 * @path: The object path
 * @returns: A newly allocated #ConduitGConduit 
 *
 * Package private constructor. Use conduit_g_application_get_dataprovider
 * as the public api.
 */
ConduitGConduit*
conduit_g_conduit_new (ConduitGApplication *application, gchar *path)
{
	ConduitGConduit 			*conduit;
	DBusGConnection 			*connection;
	DBusGProxy 					*proxy;

	conduit = CONDUIT_G_CONDUIT (g_object_new (CONDUIT_TYPE_G_CONDUIT, NULL));
	conduit->priv->application = application;
	
	g_object_ref (application);
	
	/* We need to react if the application is closed as we 
	 * are invalid in that case
	g_signal_connect (application, "closed", 
					  G_CALLBACK(_conduit_application_closed), NULL); */
	
	connection = dbus_g_bus_get (DBUS_BUS_SESSION, NULL);
	proxy = dbus_g_proxy_new_for_name (connection,
									   CONDUIT_CONDUIT_DBUS_NAME,
									   path,
									   CONDUIT_CONDUIT_DBUS_INTERFACE);
	conduit->priv->proxy = proxy;
	
	dbus_g_proxy_add_signal (proxy, "SyncStarted", G_TYPE_INVALID);
	dbus_g_proxy_add_signal (proxy, "SyncProgress", G_TYPE_DOUBLE, G_TYPE_INVALID);
	dbus_g_proxy_add_signal (proxy, "SyncCompleted", 
							 G_TYPE_BOOLEAN,G_TYPE_BOOLEAN,G_TYPE_BOOLEAN,G_TYPE_INVALID);
	dbus_g_proxy_add_signal (proxy, "SyncConflict", G_TYPE_INVALID);
	
	dbus_g_proxy_connect_signal (proxy,
								 "SyncStarted",
								 G_CALLBACK(_dispatch_sync_started),
								 conduit, NULL);

	dbus_g_proxy_connect_signal (proxy,
								 "SyncProgress",
								 G_CALLBACK(_dispatch_sync_progress),
								 conduit, NULL);
	
	dbus_g_proxy_connect_signal (proxy,
								 "SyncCompleted",
								 G_CALLBACK(_dispatch_sync_completed),
								 conduit, NULL);
	
	dbus_g_proxy_connect_signal (proxy,
								 "SyncConflict",
								 G_CALLBACK(_dispatch_sync_conflict),
								 conduit, NULL);
	
	return conduit;
}

gboolean
conduit_g_conduit_sync (ConduitGConduit *conduit)
{
	GError			*error;

	g_return_val_if_fail (CONDUIT_IS_G_CONDUIT (conduit), FALSE);
	
	error = NULL;
	if(!org_conduit_Conduit_sync(conduit->priv->proxy, &error)) {
		g_critical ("Error calling sync: %s\n", error->message);
		g_error_free (error);
		return FALSE;
	}
	return TRUE;
}

const gchar*
conduit_g_conduit_get_object_path (ConduitGConduit *conduit)
{
	g_return_val_if_fail (CONDUIT_IS_G_CONDUIT (conduit), NULL);
	return dbus_g_proxy_get_path(conduit->priv->proxy);
}

static void	
_dispatch_sync_started (DBusGProxy *proxy, ConduitGConduit *conduit)
{
	g_signal_emit (conduit, g_conduit_signals[SYNC_STARTED], 0);
}

static void
_dispatch_sync_progress (DBusGProxy *proxy, gdouble	progress, ConduitGConduit *conduit)
{
	g_signal_emit (conduit, g_conduit_signals[SYNC_PROGRESS], 0, progress);
}

static void	
_dispatch_sync_completed (DBusGProxy *proxy, gboolean aborted, gboolean errored, gboolean conflicted, ConduitGConduit 	*conduit)
{
	g_signal_emit (conduit, g_conduit_signals[SYNC_COMPLETED], 0, aborted, errored, conflicted);
}

static void	
_dispatch_sync_conflict (DBusGProxy *proxy, ConduitGConduit	*conduit)
{
	g_signal_emit (conduit, g_conduit_signals[SYNC_CONFLICT], 0);
}
