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
 
#include "evo-addressbook.h"
 
EBook *
 evo_addressbook_open(evo_location_t *location)
{
	GError *gerror = NULL;
	ESourceList *sources = NULL;
	ESource *source = NULL;
	EBook *addressbook = NULL;
	
	g_return_val_if_fail(location != NULL, FALSE);
	g_return_val_if_fail(location->uri != NULL, FALSE);

	if (strcmp(location->uri, "default")) {
		if (!e_book_get_addressbooks(&sources, NULL)) {
	  		g_warning("Error getting addressbooks: %s", gerror ? gerror->message : "None");
			g_clear_error(&gerror);
			return NULL;
		}
		
		if (!(source = evo_environment_find_source(sources, location->uri))) {
			g_warning("Error finding source \"%s\"", location->uri);
			return NULL;
		}
		
		if (!(addressbook = e_book_new(source, &gerror))) {
			g_warning("Failed to alloc new addressbook: %s", gerror ? gerror->message : "None");
			g_clear_error(&gerror);
			return NULL;
		}
	} else {
		g_debug("Opening default addressbook\n");
		if (!(addressbook = e_book_new_default_addressbook(&gerror))) {
			g_warning("Failed to alloc new default addressbook: %s", gerror ? gerror->message : "None");
			g_clear_error(&gerror);
			return NULL;
		}
	}
	
	if (!e_book_open(addressbook, TRUE, &gerror)) {
		g_warning("Failed to alloc new addressbook: %s", gerror ? gerror->message : "None");
		g_clear_error(&gerror);
		g_object_unref(addressbook);
		return NULL;
	}
	
	return addressbook;
}

char *
evo_addressbook_get_contact_vcard_string(EContact *contact)
{
	EVCard vcard;
	g_return_val_if_fail(contact != NULL, NULL);
	vcard = contact->parent;
	return e_vcard_to_string(&vcard, EVC_FORMAT_VCARD_30);
}	

GList *
evo_addressbook_get_all_contacts(EBook *addressbook)
{
	GList *changes = NULL; 
 	EBookQuery *query = e_book_query_any_field_contains("");
 	
	if (!e_book_get_contacts(addressbook, query, &changes, NULL)) {
			g_debug( "Unable to open contacts");
			return NULL;
	} 
	e_book_query_unref(query);
	return changes;
}

GList *
evo_addressbook_get_all_contacts_vcards(EBook *addressbook)
{
	GList *changes = NULL; 
	GList *vcards = NULL;
 	EBookQuery *query = e_book_query_any_field_contains("");
 	
	if (!e_book_get_contacts(addressbook, query, &changes, NULL)) {
			g_debug( "Unable to open contacts");
			return NULL;
	} 
	while(changes != NULL)
	{
		EContact *contact = E_CONTACT(changes->data);
		//prepend is faster
		vcards = g_list_prepend(vcards, evo_addressbook_get_contact_vcard_string(contact));
		changes = changes->next;
	}
	g_list_free(changes);
	e_book_query_unref(query);
	return vcards;
}
 
