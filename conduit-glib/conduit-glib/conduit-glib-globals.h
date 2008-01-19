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

#ifndef _CONDUIT_GLIB_GLOBALS_H_
#define _CONDUIT_GLIB_GLOBALS_H_

#include <glib.h>

G_BEGIN_DECLS

#define CONDUIT_APPLICATION_DBUS_NAME 		"org.conduit.Application"
#define CONDUIT_APPLICATION_DBUS_INTERFACE 	"org.conduit.Application"
#define CONDUIT_APPLICATION_DBUS_PATH		"/"

#define CONDUIT_DATAPROVIDER_DBUS_NAME 		"org.conduit.DataProvider"
#define CONDUIT_DATAPROVIDER_DBUS_INTERFACE	"org.conduit.DataProvider"

#define CONDUIT_CONDUIT_DBUS_NAME 		"org.conduit.Conduit"
#define CONDUIT_CONDUIT_DBUS_INTERFACE	"org.conduit.Conduit"

#define CONDUIT_SYNCSET_DBUS_NAME 		"org.conduit.SyncSet"
#define CONDUIT_SYNCSET_DBUS_INTERFACE	"org.conduit.SyncSet"

G_END_DECLS

#endif /* _CONDUIT_GLIB_GLOBALS_H_ */
