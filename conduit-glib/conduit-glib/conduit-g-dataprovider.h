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

#ifndef _CONDUIT_G_DATAPROVIDER_H_
#define _CONDUIT_G_DATAPROVIDER_H_

#include <glib-object.h>
#include <conduit-glib/conduit-g-application.h>

G_BEGIN_DECLS

#define CONDUIT_TYPE_G_DATAPROVIDER             (conduit_g_dataprovider_get_type ())
#define CONDUIT_G_DATAPROVIDER(obj)             (G_TYPE_CHECK_INSTANCE_CAST ((obj), CONDUIT_TYPE_G_DATAPROVIDER, ConduitGDataprovider))
#define CONDUIT_G_DATAPROVIDER_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST ((klass), CONDUIT_TYPE_G_DATAPROVIDER, ConduitGDataproviderClass))
#define CONDUIT_IS_G_DATAPROVIDER(obj)          (G_TYPE_CHECK_INSTANCE_TYPE ((obj), CONDUIT_TYPE_G_DATAPROVIDER))
#define CONDUIT_IS_G_DATAPROVIDER_CLASS(klass)  (G_TYPE_CHECK_CLASS_TYPE ((klass), CONDUIT_TYPE_G_DATAPROVIDER))
#define CONDUIT_G_DATAPROVIDER_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS ((obj), CONDUIT_TYPE_G_DATAPROVIDER, ConduitGDataproviderClass))

/* Public structs */
/* Foward declared in application.h 
typedef struct _ConduitGDataprovider ConduitGDataprovider; */
typedef struct _ConduitGDataproviderClass ConduitGDataproviderClass;

/* Private structs */
typedef struct _ConduitGDataproviderPrivate ConduitGDataproviderPrivate;

struct _ConduitGDataproviderClass
{
	GObjectClass parent_class;
};

struct _ConduitGDataprovider
{
	GObject 					parent_instance;
	ConduitGDataproviderPrivate *priv;
};

/* Public methods */
GType 			conduit_g_dataprovider_get_type 			(void) G_GNUC_CONST;

GHashTable*		conduit_g_dataprovider_get_information 		(ConduitGDataprovider *dataprovider);

void			conduit_g_dataprovider_configure 			(ConduitGDataprovider *dataprovider);

gboolean		conduit_g_dataprovider_is_pending 			(ConduitGDataprovider *dataprovider);

gboolean		conduit_g_dataprovider_add_data 			(ConduitGDataprovider *dataprovider, gchar *uri);

void			conduit_g_dataprovider_configure 			(ConduitGDataprovider *dataprovider);

gboolean		conduit_g_dataprovider_is_configured 		(ConduitGDataprovider *dataprovider);

gboolean		conduit_g_dataprovider_set_configuration_xml(ConduitGDataprovider *dataprovider, gchar *xml);

gchar *			conduit_g_dataprovider_get_configuration_xml(ConduitGDataprovider *dataprovider);

ConduitGApplication*	
				conduit_g_dataprovider_get_application 		(ConduitGDataprovider *dataprovider);

G_END_DECLS

#endif /* _CONDUIT_G_DATAPROVIDER_H_ */
