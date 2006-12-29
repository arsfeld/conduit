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

#include "evo-contact.h"
 
char *
evo_contact_get_vcard_string(EContact *obj)
{
	g_return_val_if_fail(obj != NULL, NULL);
	g_return_val_if_fail(E_IS_CONTACT(obj), NULL);

	EVCard vcard = obj->parent;
	return e_vcard_to_string(&vcard, EVC_FORMAT_VCARD_30);
}

char *
evo_contact_get_name(EContact *obj)
{
	g_return_val_if_fail(obj != NULL, NULL);
	g_return_val_if_fail(E_IS_CONTACT(obj), NULL);
	
	EContactName *name = (EContactName *)e_contact_get(obj, E_CONTACT_NAME);

	return e_contact_name_to_string (name);
}

char *
evo_contact_get_uid(EContact *obj)
{
	g_return_val_if_fail(obj != NULL, NULL);
	g_return_val_if_fail(E_IS_CONTACT(obj), NULL);
	
	return  (char *)e_contact_get(obj, E_CONTACT_UID);
}

GdkPixbuf *
evo_contact_get_photo (EContact *contact, gint pixbuf_size)
{
	GdkPixbuf *pixbuf = NULL;
	EContactPhoto *photo = e_contact_get (contact, E_CONTACT_PHOTO);
	if (photo) {
		GdkPixbufLoader *loader;

		loader = gdk_pixbuf_loader_new ();

		if (photo->type == E_CONTACT_PHOTO_TYPE_INLINED) {
			if (gdk_pixbuf_loader_write (loader, (guchar *) photo->data.inlined.data, photo->data.inlined.length, NULL))
				pixbuf = gdk_pixbuf_loader_get_pixbuf (loader);
		}

		if (pixbuf) {
			GdkPixbuf *tmp;
			gint width = gdk_pixbuf_get_width (pixbuf);
			gint height = gdk_pixbuf_get_height (pixbuf);
			double scale = 1.0;

			if (height > width) {
				scale = pixbuf_size / (double) height;
			} else {
				scale = pixbuf_size / (double) width;
			}

			if (scale < 1.0) {
				tmp = gdk_pixbuf_scale_simple (pixbuf, width * scale, height * scale, GDK_INTERP_BILINEAR);
				g_object_unref (pixbuf);
				pixbuf = tmp;
			}
		}
		e_contact_photo_free (photo);
	}
	return pixbuf;
}


