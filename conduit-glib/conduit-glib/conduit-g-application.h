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

#ifndef _CONDUIT_G_APPLICATION_H_
#define _CONDUIT_G_APPLICATION_H_

#include <glib-object.h>
#include <dbus/dbus-glib.h>

G_BEGIN_DECLS

#define CONDUIT_TYPE_G_APPLICATION             (conduit_g_application_get_type ())
#define CONDUIT_G_APPLICATION(obj)             (G_TYPE_CHECK_INSTANCE_CAST ((obj), CONDUIT_TYPE_G_APPLICATION, ConduitGApplication))
#define CONDUIT_G_APPLICATION_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST ((klass), CONDUIT_TYPE_G_APPLICATION, ConduitGApplicationClass))
#define CONDUIT_IS_G_APPLICATION(obj)          (G_TYPE_CHECK_INSTANCE_TYPE ((obj), CONDUIT_TYPE_G_APPLICATION))
#define CONDUIT_IS_G_APPLICATION_CLASS(klass)  (G_TYPE_CHECK_CLASS_TYPE ((klass), CONDUIT_TYPE_G_APPLICATION))
#define CONDUIT_G_APPLICATION_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS ((obj), CONDUIT_TYPE_G_APPLICATION, ConduitGApplicationClass))

// Public structs
typedef struct _ConduitGApplication ConduitGApplication;
typedef struct _ConduitGApplicationClass ConduitGApplicationClass;

// Private structs
typedef struct _ConduitGApplicationPrivate ConduitGApplicationPrivate;

// Forward declarations
typedef struct _ConduitGDataprovider ConduitGDataprovider;
typedef struct _ConduitGConduit ConduitGConduit;
ConduitGDataprovider*	conduit_g_dataprovider_new (ConduitGApplication *application, gchar *path);
const gchar*			conduit_g_dataprovider_get_object_path (ConduitGDataprovider *dataprovider);
ConduitGConduit*		conduit_g_conduit_new (ConduitGApplication *application, gchar *path);
const gchar*			conduit_g_conduit_get_object_path (ConduitGConduit *conduit);

struct _ConduitGApplicationClass
{
	GObjectClass parent_class;
};

struct _ConduitGApplication
{
	GObject 				parent_instance;
	ConduitGApplicationPrivate 	*priv;
};


// Public methods
GType          			conduit_g_application_get_type 		(void) G_GNUC_CONST;

ConduitGApplication* 	conduit_g_application_new 			(void);

gchar**					conduit_g_application_get_all_dataproviders (ConduitGApplication *application);

ConduitGDataprovider*	conduit_g_application_get_dataprovider (ConduitGApplication *application, const gchar *name);

ConduitGConduit *		conduit_g_application_build_conduit (ConduitGApplication *application, ConduitGDataprovider *source, ConduitGDataprovider *sink);

G_END_DECLS

#endif /* _CONDUIT_G_APPLICATION_H_ */
