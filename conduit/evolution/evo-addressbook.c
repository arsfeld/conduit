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
#include "evo-contact.h"
 
 /**
 * Split a string of tokens separated by whitespace into an array of tokens.
 */
static GArray *
split_query_string (const gchar *str)
{
	GArray *parts = g_array_sized_new (FALSE, FALSE, sizeof (char *), 2);
	PangoLogAttr *attrs;
	guint str_len = strlen (str), word_start = 0, i;

	attrs = g_new0 (PangoLogAttr, str_len + 1);
	/* TODO: do we need to specify a particular language or is NULL ok? */
	pango_get_log_attrs (str, -1, -1, NULL, attrs, str_len + 1);

	for (i = 0; i < str_len + 1; i++) {
		char *start_word, *end_word, *word;
		if (attrs[i].is_word_end) {
			start_word = g_utf8_offset_to_pointer (str, word_start);
			end_word = g_utf8_offset_to_pointer (str, i);
			word  = g_strndup (start_word, end_word - start_word);
			g_array_append_val (parts, word);
		}
		if (attrs[i].is_word_start) {
			word_start = i;
		}
	}
	g_free (attrs);
	return parts;
}

/**
 * Create a query which looks for the specified string in a contact's full name, email addresses and
 * nick name.
 */
static EBookQuery *
create_query (const char* s)
{
	EBookQuery *query;
	GArray *parts = split_query_string (s);
	EBookQuery ***field_queries;
	EBookQuery **q;
	guint j;
	int i;

	q = g_new0 (EBookQuery *, n_search_fields);
	field_queries = g_new0 (EBookQuery **, n_search_fields);

	for (i = 0; i < n_search_fields; i++) {
		field_queries[i] = g_new0 (EBookQuery *, parts->len);
		for (j = 0; j < parts->len; j++) {
			field_queries[i][j] = e_book_query_field_test (search_fields[i], E_BOOK_QUERY_CONTAINS, g_array_index (parts, gchar *, j));
		}
		q[i] = e_book_query_and (parts->len, field_queries[i], TRUE);
	}
	g_array_free (parts, TRUE);

	query = e_book_query_or (n_search_fields, q, TRUE);

	for (i = 0; i < n_search_fields; i++) {
		g_free (field_queries[i]);
	}
	g_free (field_queries);
	g_free (q);

	return query;
}

static gboolean 
commit_contact(EBook *book, EContact *contact, evo_change_t change)
{
	GError *gerror = NULL;
	char *uid = NULL;
	
	g_return_val_if_fail(contact != NULL, FALSE);
	switch (change) 
	{
		case CHANGE_DELETED:
			uid = evo_contact_get_uid(contact);
			if (!e_book_remove_contact(book, uid, NULL)) {
				g_warning("Unable to delete contact");
				return FALSE;
			}
			break;
		case CHANGE_ADDED:
			e_contact_set(contact, E_CONTACT_UID, NULL);
			if (!e_book_add_contact(book, contact, &gerror)) {
				g_warning("Unable to add contact: %s", gerror ? gerror->message : "None");
				return FALSE;
			}
			break;
		case CHANGE_MODIFIED:
			//contact = e_contact_new_from_vcard(osync_change_get_data(change));
			//e_contact_set(contact, E_CONTACT_UID, g_strdup(uid));
			//osync_trace(TRACE_INTERNAL, "ABout to modify vcard:\n%s", e_vcard_to_string(&(contact->parent), EVC_FORMAT_VCARD_30));
			if (e_book_commit_contact(book, contact, &gerror)) {
				uid = e_contact_get_const(contact, E_CONTACT_UID);
			} else {
				/* try to add */
				g_warning("unable to mod contact: %s", gerror ? gerror->message : "None");
				
				g_clear_error(&gerror);
				if (e_book_add_contact(book, contact, &gerror)) {
					//uid = e_contact_get_const(contact, E_CONTACT_UID);
					//osync_change_set_uid(change, uid);
				//} else {
					g_warning("Unable to modify or add contact: %s", gerror ? gerror->message : "None");
					return FALSE;
				}
			}
			break;
		default:
			g_critical("UNKNOWN CHANGE TYPE\n");
	}
	return TRUE;
}
 
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

gboolean 
evo_addressbook_get_changed_contacts(EBook *addressbook, GList *added, GList *modified, GList *deleted, char *change_id)
{

	GList *changes = NULL;
	EBookChange *ebc = NULL;
	GList *l = NULL;
	char *uid = NULL;
	
	if (!e_book_get_changes(addressbook, change_id, &changes, NULL)) {
			g_warning("Unable to open changed contacts");
			return FALSE;
	}
	
	g_debug("Found %i changes for change-ID %s", g_list_length(changes), change_id);
		
	for (l = changes; l; l = l->next) 
	{
		ebc = (EBookChange *)l->data;
		uid = g_strdup(e_contact_get_const(ebc->contact, E_CONTACT_UID));
		e_contact_set(ebc->contact, E_CONTACT_UID, NULL);
		switch (ebc->change_type) 
		{
			case E_BOOK_CHANGE_CARD_ADDED:
					added = g_list_prepend(added, ebc->contact);
					break;
				case E_BOOK_CHANGE_CARD_MODIFIED:
					modified = g_list_prepend(modified, ebc->contact);
					break;
				case E_BOOK_CHANGE_CARD_DELETED:
					deleted = g_list_prepend(deleted, ebc->contact);
					break;
		}
		g_free(uid);
	}
	return TRUE;
}

/*
 * Note: you may get a message "WARNING **: FIXME: wait for completion unimplemented"
 * if you call search_sync but are not running the gobject main loop.
 * This appears to be harmless: http://bugzilla.gnome.org/show_bug.cgi?id=314544
 */
GList *
evo_addressbook_free_text_search(EBook *book, const char *query)
{
	GList *contacts = NULL;

	EBookQuery *book_query = create_query (query);
	e_book_get_contacts (book, book_query, &contacts, NULL);
	e_book_query_unref (book_query);
	return contacts;
}
