/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 4; tab-width: 4 -*- */
/*
 * main.c
 * Copyright (C) John Stowers 2006 <john.stowers@gmail.com>
 * 
 * main.c is free software.
 * 
 * You may redistribute it and/or modify it under the terms of the
 * GNU General Public License, as published by the Free Software
 * Foundation; either version 2 of the License, or (at your option)
 * any later version.
 * 
 * main.c is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with main.c.  If not, write to:
 * 	The Free Software Foundation, Inc.,
 * 	51 Franklin Street, Fifth Floor
 * 	Boston, MA  02110-1301, USA.
 */

#include <stdio.h>

#include "evo-environment.h"
#include "evo-addressbook.h"

int
main (int argc, char *argv[])
{
	GList *cals = evo_environment_list_calendars();
	printf("Listing Calendars:\n");
	while(cals != NULL)
	 {
	 		evo_location_t *path = cals->data;
	 		printf("Path: %s\nURI:%s\n\n", path->name, path->uri);
			cals = cals->next;
	}

	GList *tasks = evo_environment_list_tasks();
	printf("Listing Tasks:\n");
	while(tasks != NULL)
	 {
	 		evo_location_t *path = tasks->data;
	 		printf("Path: %s\nURI:%s\n\n", path->name, path->uri);
			tasks = tasks->next;
	}
	
	GList *books = evo_environment_list_addressbooks();
	printf("Listing Addressbooks:\n");
	while(books != NULL)
	 {
	 		evo_location_t *path = books->data;
	 		printf("Path: %s\nURI:%s\n\n", path->name, path->uri);
			books = books->next;
	}	
	
	//List the contents of the default address book
	evo_location_t loc;
	loc.uri = "default";
	
	EBook *addressbook = evo_addressbook_open(&loc);
	GList *list = evo_addressbook_get_all_contacts_vcards(addressbook);
	while(list != NULL)
	{
		printf("%s",(char *)list->data);
		list = list->next;
	}
	
	return 0;
}
