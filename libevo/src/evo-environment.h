/*
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU Library General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#ifndef EVO_ENVIRONMENT_H
#define EVO_ENVIRONMENT_H

#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <glib-object.h>

#include <libecal/e-cal.h>
#include <libebook/e-book.h>
#include <libebook/e-vcard.h>

G_BEGIN_DECLS

typedef struct evo2_location {
	char *name;
	char *uri;
} evo_location_t;

GList *evo_environment_list_calendars();
GList *evo_environment_list_tasks();
GList *evo_environment_list_addressbooks();
ESource *evo_environment_find_source(ESourceList *list, char *uri);

G_END_DECLS

#endif /* EVO_ENVIRONMENT_H */
