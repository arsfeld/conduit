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

#ifndef _CONDUIT_G_CONDUIT_H_
#define _CONDUIT_G_CONDUIT_H_

#include <glib-object.h>
#include <conduit-glib/conduit-g-application.h>

G_BEGIN_DECLS

#define CONDUIT_TYPE_G_CONDUIT             (conduit_g_conduit_get_type ())
#define CONDUIT_G_CONDUIT(obj)             (G_TYPE_CHECK_INSTANCE_CAST ((obj), CONDUIT_TYPE_G_CONDUIT, ConduitGConduit))
#define CONDUIT_G_CONDUIT_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST ((klass), CONDUIT_TYPE_G_CONDUIT, ConduitGConduitClass))
#define CONDUIT_IS_G_CONDUIT(obj)          (G_TYPE_CHECK_INSTANCE_TYPE ((obj), CONDUIT_TYPE_G_CONDUIT))
#define CONDUIT_IS_G_CONDUIT_CLASS(klass)  (G_TYPE_CHECK_CLASS_TYPE ((klass), CONDUIT_TYPE_G_CONDUIT))
#define CONDUIT_G_CONDUIT_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS ((obj), CONDUIT_TYPE_G_CONDUIT, ConduitGConduitClass))

/* Public structs */
/* Foward declared in application.h 
typedef struct _ConduitGConduit ConduitGConduit; */
typedef struct _ConduitGConduitClass ConduitGConduitClass;

/* Private structs */
typedef struct _ConduitGConduitPrivate ConduitGConduitPrivate;

struct _ConduitGConduitClass
{
	GObjectClass parent_class;
};

struct _ConduitGConduit
{
	GObject 					parent_instance;
	ConduitGConduitPrivate *priv;
};

/* Public methods */
GType 			conduit_g_conduit_get_type 			(void) G_GNUC_CONST;

gboolean		conduit_g_conduit_sync 				(ConduitGConduit *conduit);

G_END_DECLS

#endif /* _CONDUIT_G_CONDUIT_H_ */
