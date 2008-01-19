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

#include "conduit-g-syncset.h"
#include "conduit-syncset-bindings.h"
#include "conduit-g-application.h"
#include "conduit-g-conduit.h"
#include "conduit-glib-globals.h"

struct _ConduitGSyncsetPrivate {
	ConduitGApplication 	*application;
	DBusGProxy 				*proxy;
	DBusGProxyCall			*proxy_request_call;
};

/* Private methods */

G_DEFINE_TYPE (ConduitGSyncset, conduit_g_syncset, G_TYPE_OBJECT);

static void
conduit_g_syncset_init (ConduitGSyncset *syncset)
{
	ConduitGSyncsetPrivate *priv;
	
	priv = g_new0 (ConduitGSyncsetPrivate, 1);
	priv->application = NULL;
	priv->proxy = NULL;
	priv->proxy_request_call = NULL;
	
	syncset->priv = priv;
}

static void
conduit_g_syncset_finalize (GObject *object)
{
	ConduitGSyncset 		*syncset;
	ConduitGSyncsetPrivate *priv;
	
	syncset = CONDUIT_G_SYNCSET(object);
	priv = syncset->priv;
	
	g_object_unref (priv->application);
	
	g_free (syncset->priv);

	G_OBJECT_CLASS (conduit_g_syncset_parent_class)->finalize (object);
}

static void
conduit_g_syncset_class_init (ConduitGSyncsetClass *klass)
{
	GObjectClass* object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = conduit_g_syncset_finalize;
}

ConduitGSyncset*
conduit_g_syncset_new (ConduitGApplication *application, gchar *path)
{
	ConduitGSyncset 			*syncset;
	DBusGConnection 			*connection;
	DBusGProxy 					*proxy;

	g_return_val_if_fail (CONDUIT_IS_G_APPLICATION (application), NULL);
	
	syncset = CONDUIT_G_SYNCSET (g_object_new (CONDUIT_TYPE_G_SYNCSET, NULL));
	syncset->priv->application = application;
	
	g_object_ref (application);
	
	/* We need to react if the application is closed as we 
	 * are invalid in that case
	g_signal_connect (application, "closed", 
					  G_CALLBACK(_conduit_application_closed), NULL); */
	
	connection = dbus_g_bus_get (DBUS_BUS_SESSION, NULL);
	proxy = dbus_g_proxy_new_for_name (connection,
									   CONDUIT_SYNCSET_DBUS_NAME,
									   path,
									   CONDUIT_SYNCSET_DBUS_INTERFACE);
	syncset->priv->proxy = proxy;
	
	return syncset;
}

gboolean
conduit_g_syncset_add_conduit (ConduitGSyncset *syncset, ConduitGConduit *conduit)
{
	GError			*error;
	const gchar		*path;

	g_return_val_if_fail (CONDUIT_IS_G_CONDUIT (conduit), FALSE);
	
	path = conduit_g_conduit_get_object_path(conduit);
	
	error = NULL;
	if(!org_conduit_SyncSet_add_conduit(syncset->priv->proxy, path, &error)) {
		g_critical ("Error adding conduit to syncset: %s\n", error->message);
		g_error_free (error);
		return FALSE;
	}
	return TRUE;
}

const gchar*
conduit_g_syncset_get_object_path (ConduitGSyncset *syncset)
{
	g_return_val_if_fail (CONDUIT_IS_G_SYNCSET (syncset), NULL);
	return dbus_g_proxy_get_path(syncset->priv->proxy);
}

