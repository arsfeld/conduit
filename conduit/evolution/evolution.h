
#ifndef __CONDUIT_EVOLUTION_H__
#define __CONDUIT_EVOLUTION_H__

#include <glib.h>
#include <glib/gstring.h>
#include <glib/gtypes.h>
#include <libebook/e-book.h>
#include <libebook/e-vcard.h>
#include <libebook/e-contact.h>
#include <pango/pango.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <string.h>

G_BEGIN_DECLS

typedef struct _Hit {
	gchar *text;
	gchar *email;
    gchar *uid;
	GdkPixbuf *pixbuf;
} Hit;

void free_hit (Hit *hit, gpointer unused);

void init (void);

void set_pixbuf_size (int size);

GList * search_sync (const char *query,
                     int         max_results);

G_END_DECLS

#endif /* __CONDUIT_EVOLUTION_H__ */

