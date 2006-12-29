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

EBook *evo_addressbook_open(evo_location_t *location);
char *evo_addressbook_get_contact_vcard_string(EContact *contact);
GList *evo_addressbook_get_all_contacts(EBook *addressbook);
GList *evo_addressbook_get_all_contacts_vcards(EBook *addressbook);

G_END_DECLS

#endif /* EVO_ADDRESSBOOK_H */ 
 
 
