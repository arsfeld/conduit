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

#include "conduit-g-dataprovider.h"
#include "conduit-dataprovider-bindings.h"
#include "conduit-g-application.h"
#include "conduit-glib-globals.h"

struct _ConduitGDataproviderPrivate {
	ConduitGApplication 	*application;
	DBusGProxy 				*proxy;
	DBusGProxyCall			*proxy_request_call;
};

/* Private methods */


G_DEFINE_TYPE (ConduitGDataprovider, conduit_g_dataprovider, G_TYPE_OBJECT);

/**
 * SECTION:conduit-g-dataprovider
 * @short_description: Represents a dataprovider
 * @see_also: #ConduitGApplication
 *
 * #ConduitGDataprovider is a client side representation of a dataprovider. A dataprovider is
 * created via a #ConduitGApplication object's #conduit_g_application_get_dataprovider
 *
 */

static void
conduit_g_dataprovider_init (ConduitGDataprovider *dataprovider)
{
	ConduitGDataproviderPrivate *priv;
	
	priv = g_new0 (ConduitGDataproviderPrivate, 1);
	priv->application = NULL;
	priv->proxy = NULL;
	priv->proxy_request_call = NULL;
	
	dataprovider->priv = priv;
}

static void
conduit_g_dataprovider_finalize (GObject *object)
{
	ConduitGDataprovider 		*dataprovider;
	ConduitGDataproviderPrivate *priv;
	
	dataprovider = CONDUIT_G_DATAPROVIDER(object);
	priv = dataprovider->priv;
	
	g_object_unref (priv->application);
	
	g_free (dataprovider->priv);

	G_OBJECT_CLASS (conduit_g_dataprovider_parent_class)->finalize (object);
}

static void
conduit_g_dataprovider_class_init (ConduitGDataproviderClass *klass)
{
	GObjectClass* object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = conduit_g_dataprovider_finalize;
}

/**
 * conduit_g_dataprovider_new
 * @application: The session to be parent of the new dataprovider
 * @query: The query the dataprovider should run
 * @returns: A newly allocated #ConduitGDataprovider 
 *
 * Package private constructor. Use conduit_g_application_get_dataprovider
 * as the public api.
 */
ConduitGDataprovider*
conduit_g_dataprovider_new (ConduitGApplication *application, gchar *path)
{
	ConduitGDataprovider 		*dataprovider;
	DBusGConnection 			*connection;
	DBusGProxy 					*proxy;

	dataprovider = CONDUIT_G_DATAPROVIDER (g_object_new (CONDUIT_TYPE_G_DATAPROVIDER, NULL));
	dataprovider->priv->application = application;
	
	g_object_ref (application);
	
	/* We need to react if the application is closed as we 
	 * are invalid in that case
	g_signal_connect (application, "closed", 
					  G_CALLBACK(_conduit_application_closed), NULL); */
	
	connection = dbus_g_bus_get (DBUS_BUS_SESSION, NULL);
	proxy = dbus_g_proxy_new_for_name (connection,
									   CONDUIT_DATAPROVIDER_DBUS_NAME,
									   path,
									   CONDUIT_DATAPROVIDER_DBUS_INTERFACE);
	dataprovider->priv->proxy = proxy;
	
	return dataprovider;
}

GHashTable*
conduit_g_dataprovider_get_information (ConduitGDataprovider *dataprovider)
{
	GHashTable		*info;
	GError			*error;
	
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), NULL);

	error = NULL;
	if (!org_conduit_DataProvider_get_information(dataprovider->priv->proxy, &info, &error)) {
		g_critical ("Error getting information: %s\n", error->message);
		g_error_free (error);
		return NULL;
	}
	return info;
}

void
conduit_g_dataprovider_configure (ConduitGDataprovider *dataprovider)
{
	GError			*error;
	
	g_return_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider));
	
	error = NULL;
	if (!org_conduit_DataProvider_configure(dataprovider->priv->proxy, &error)) {
		g_critical ("Error configuring dataprovider: %s\n", error->message);
		g_error_free (error);
	}
}

gboolean
conduit_g_dataprovider_is_pending (ConduitGDataprovider *dataprovider)
{
	gboolean		pending;
	GError			*error;

	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), FALSE);
	
	error = NULL;
	if(!org_conduit_DataProvider_is_configured(dataprovider->priv->proxy, &pending, &error)) {
		g_critical ("Error calling is_pending: %s\n", error->message);
		g_error_free (error);
		return FALSE;
	}
	return pending;
}

gboolean
conduit_g_dataprovider_add_data (ConduitGDataprovider *dataprovider, gchar *uri)
{
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), FALSE);
	return FALSE;
}

gboolean
conduit_g_dataprovider_is_configured (ConduitGDataprovider *dataprovider)
{
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), FALSE);
	return FALSE;
}

gboolean
conduit_g_dataprovider_set_configuration_xml (ConduitGDataprovider *dataprovider, gchar *xml)
{
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), FALSE);
	return FALSE;
}

gchar *
conduit_g_dataprovider_get_configuration_xml (ConduitGDataprovider *dataprovider)
{
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), NULL);
	return NULL;
}

ConduitGApplication*
conduit_g_dataprovider_get_application (ConduitGDataprovider *dataprovider)
{
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), NULL);
	return dataprovider->priv->application;
}

const gchar*
conduit_g_dataprovider_get_object_path (ConduitGDataprovider *dataprovider)
{
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (dataprovider), NULL);
	return dbus_g_proxy_get_path(dataprovider->priv->proxy);
}

/* Callback for the closed signal on the session 
static void
_conduit_application_closed (ConduitGDataprovider	*dataprovider)
{
	if (!dataprovider->priv->closed) {
		conduit_g_dataprovider_close (dataprovider);
	}
} */
