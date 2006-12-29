/*
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Library General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor Boston, MA 02110-1301,  USA
 */

#ifndef EVO_ADDRESSBOOK_H
#define EVO_ADDRESSBOOK_H

#include "evo-environment.h"

G_BEGIN_DECLS

static EContactField search_fields[] = { E_CONTACT_FULL_NAME, E_CONTACT_EMAIL, E_CONTACT_NICKNAME, 0 };
static int n_search_fields = G_N_ELEMENTS (search_fields) - 1;

/* Private */
static EBookQuery *create_query (const char* s);
static GArray *split_query_string (const gchar *str);
static gboolean commit_contact(EBook *book, EContact *contact, evo_change_t change);

/* Public */
EBook *evo_addressbook_open(evo_location_t *location);
GList *evo_addressbook_get_all_contacts(EBook *addressbook);
gboolean evo_addressbook_get_changed_contacts(EBook *addressbook, GList *added, GList *modified, GList *deleted, char *change_id);
GList *evo_addressbook_free_text_search(EBook *book, const char *query);

G_END_DECLS

#endif /* EVO_ADDRESSBOOK_H */ 
 
 
