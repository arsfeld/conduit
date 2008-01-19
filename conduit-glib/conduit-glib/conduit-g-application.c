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

#include "conduit-g-application.h"
#include "conduit-application-bindings.h"
#include "conduit-g-dataprovider.h"
#include "conduit-g-conduit.h"
#include "conduit-marshal.h"

#define CONDUIT_APPLICATION_DBUS_NAME "org.conduit.Application"
#define CONDUIT_APPLICATION_DBUS_INTERFACE "org.conduit.Application"
#define CONDUIT_APPLICATION_DBUS_PATH "/"

struct _ConduitGApplicationPrivate {
	DBusGProxy 				*proxy;
	DBusGConnection			*connection;
	DBusGProxyCall			*session_request_call;
};

/* Property ids */
enum
{
	PROP_0,

	PROP_VERSION,
	
	LAST_PROPERTY
};

/* Signals */
enum
{
	DATAPROVIDER_AVAILABLE,
	DATAPROVIDER_UNAVAILABLE,
	
	LAST_SIGNAL
};

static guint g_application_signals[LAST_SIGNAL] = { 0 };

/* Private methods */
static void	_dispatch_dataprovider_available 		(DBusGProxy 	*proxy,
													 const gchar	*key,
													 ConduitGApplication 	*application);

static void	_dispatch_dataprovider_unavailable 		(DBusGProxy 	*proxy,
													 const gchar	*key,
													 ConduitGApplication *application);

G_DEFINE_TYPE (ConduitGApplication, conduit_g_application, G_TYPE_OBJECT);

static void
conduit_g_application_finalize (GObject *application_obj)
{
	ConduitGApplication 			*application;
	ConduitGApplicationPrivate		*priv;
	
	application = CONDUIT_G_APPLICATION (application_obj);
	priv = application->priv;
	
	/* Free private members */
	if (priv->proxy) g_object_unref (priv->proxy);
	if (priv->connection) dbus_g_connection_unref (priv->connection);
	
	/* Free fundamental structs */
	g_free (application->priv);
	
	G_OBJECT_CLASS (conduit_g_application_parent_class)->finalize (application_obj);
}

static void
conduit_g_application_set_property (GObject 		*object, guint 		prop_id, 
							  const GValue 	*value,  GParamSpec *pspec)
{	
	ConduitGApplication 	*application;
	
	g_return_if_fail (CONDUIT_IS_G_APPLICATION (object));
	
	if (prop_id <= PROP_0 || prop_id >= LAST_PROPERTY) {
		G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	}
	
	application = CONDUIT_G_APPLICATION (object);
}

static void
conduit_g_application_get_property (GObject *object, guint prop_id, GValue *value, GParamSpec *pspec)
{
	ConduitGApplication			*application;
	
	g_return_if_fail (CONDUIT_IS_G_APPLICATION (object));
	
	application = CONDUIT_G_APPLICATION (object);
	
	switch (prop_id)
	{
	case PROP_VERSION:
		break;	
	default:
		G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
		return;
		break;
	}
}

static void
conduit_g_application_class_init (ConduitGApplicationClass *klass)
{
	GObjectClass* object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = conduit_g_application_finalize;
	object_class->set_property = conduit_g_application_set_property;
	object_class->get_property = conduit_g_application_get_property;	

	/* Register a signal marshaller for the SyncCompleted signal */
    dbus_g_object_register_marshaller(conduit_marshal_VOID__BOOLEAN_BOOLEAN_BOOLEAN,
									  G_TYPE_NONE, G_TYPE_BOOLEAN,G_TYPE_BOOLEAN,G_TYPE_BOOLEAN,
									  G_TYPE_INVALID);
	
	g_object_class_install_property (object_class,
	                                 PROP_VERSION,
	                                 g_param_spec_string ("version",
														  "Conduit version",
														  "Conduit version",
														  "",
														  G_PARAM_READABLE));
	
	/**
	 * ConduitGApplication::dataprovider-available
	 * @application: The object on which this signal is emitted
	 * @key: DP key
	 *
	 * Emitted when new dp is detected
	 */
	g_application_signals[DATAPROVIDER_AVAILABLE] =
		g_signal_new ("dataprovider-available",
		              G_OBJECT_CLASS_TYPE (klass),
		              G_SIGNAL_RUN_LAST,
		              0,
		              NULL, NULL,
		              g_cclosure_marshal_VOID__STRING,
		              G_TYPE_NONE, 1,
		              G_TYPE_STRING);
		              
	/**
	 * ConduitGApplication::dataprovider-unavailable
	 * @application: The object on which this signal is emitted
	 * @key: DP key
	 *
	 * Emitted when a dp goes away
	 */
	g_application_signals[DATAPROVIDER_UNAVAILABLE] =
		g_signal_new ("dataprovider-unavailable",
		              G_OBJECT_CLASS_TYPE (klass),
		              G_SIGNAL_RUN_LAST,
		              0,
		              NULL, NULL,
		              g_cclosure_marshal_VOID__STRING,
		              G_TYPE_NONE, 1,
		              G_TYPE_STRING);
}

static void
conduit_g_application_init (ConduitGApplication *application)
{
	ConduitGApplicationPrivate 	*priv;
	
	priv = g_new0 (ConduitGApplicationPrivate, 1);
	priv->proxy = NULL;

	application->priv = priv;
}

/**
 * conduit_g_application_new
 * @returns: A newly created #ConduitGApplication or %NULL if there is an error
 *           connecting to DBus session bus.
 *
 * Returns %NULL if there is an error connecting to the DBus session bus.
 */
ConduitGApplication*
conduit_g_application_new (void)
{
	ConduitGApplication 	*application;
	DBusGConnection 		*connection;
	DBusGProxy 				*proxy;
	GError 					*error;

	error = NULL;
	connection = dbus_g_bus_get (DBUS_BUS_SESSION, &error);
	
	if (connection == NULL)
    {
		g_critical ("Failed to open connection to bus: %s\n", error->message);
		g_error_free (error);
		return NULL;
	}
	
	proxy = dbus_g_proxy_new_for_name (connection,
									   CONDUIT_APPLICATION_DBUS_NAME,
									   CONDUIT_APPLICATION_DBUS_PATH,
									   CONDUIT_APPLICATION_DBUS_INTERFACE);
	
	application = CONDUIT_G_APPLICATION (g_object_new (CONDUIT_TYPE_G_APPLICATION, NULL));
	application->priv->connection = connection;
	application->priv->proxy = proxy;
	
	dbus_g_proxy_add_signal (proxy, "DataproviderAvailable", 
							 G_TYPE_STRING, G_TYPE_INVALID);
	
	dbus_g_proxy_add_signal (proxy, "DataproviderUnavailable", 
							 G_TYPE_STRING, G_TYPE_INVALID);
	
	dbus_g_proxy_connect_signal (proxy,
								 "DataproviderAvailable",
								 G_CALLBACK(_dispatch_dataprovider_available),
								 application, NULL);
	
	dbus_g_proxy_connect_signal (proxy,
								 "DataproviderUnavailable",
								 G_CALLBACK(_dispatch_dataprovider_unavailable),
								 application, NULL);
	
	return application;
}

gchar **		
conduit_g_application_get_all_dataproviders (ConduitGApplication *application)
{
	gchar 		**array;
	GError		*error;

	array = NULL;
	error = NULL;
	if (!org_conduit_Application_get_all_data_providers (application->priv->proxy, &array, &error)) {
		g_critical ("Error listing dataprovider: %s\n", error->message);
		g_error_free (error);
	}
	return array;
}

ConduitGDataprovider *
conduit_g_application_get_dataprovider (ConduitGApplication *application, const gchar *name)
{
	GError					*error;
	gchar					*path;
	ConduitGDataprovider 	*dp;
	
	error = NULL;
	path = NULL;
	if (!org_conduit_Application_get_data_provider(application->priv->proxy, name, &path, &error)) {
		g_critical ("Error getting dataprovider: %s\n", error->message);
		g_error_free (error);
		return NULL;
	}
	dp = conduit_g_dataprovider_new(application, path);
	return dp;
}

ConduitGConduit *
conduit_g_application_build_conduit (ConduitGApplication *application, ConduitGDataprovider *source, ConduitGDataprovider *sink)
{
	GError					*error;
	const gchar				*source_path, *sink_path;
	gchar					*conduit_path;
	ConduitGConduit 		*conduit;

	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (source), NULL);
	g_return_val_if_fail (CONDUIT_IS_G_DATAPROVIDER (sink), NULL);
	
	source_path = conduit_g_dataprovider_get_object_path(source);
	sink_path = conduit_g_dataprovider_get_object_path(sink);

	error = NULL;
	if (!org_conduit_Application_build_conduit(application->priv->proxy, source_path, sink_path, &conduit_path, &error)) {
		g_critical ("Error building conduit: %s\n", error->message);
		g_error_free (error);
		return NULL;
	}
	conduit = conduit_g_conduit_new(application, conduit_path);
	return conduit;
}

static void
_dispatch_dataprovider_available (DBusGProxy 	*proxy,
					  const gchar	*key,
                      ConduitGApplication *application)
{	
	g_signal_emit (application, g_application_signals[DATAPROVIDER_AVAILABLE], 0, key);
}

static void
_dispatch_dataprovider_unavailable (DBusGProxy 		*proxy,
						const gchar		*key,
						ConduitGApplication 	*application)
{	
	g_signal_emit (application, g_application_signals[DATAPROVIDER_UNAVAILABLE], 0, key);
}


