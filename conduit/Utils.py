import sys
import gtk, gobject
import conduit

ICON_THEME = gtk.icon_theme_get_default()
# We load the icon file, and if it fails load an empty one
# If the iconfile is a path starting with /, load the file
# else try to load a stock or named icon name
def load_icon(icon, width=conduit.ICON_HEIGHT, height=conduit.ICON_HEIGHT):
    pixbuf = None
    if icon != None and icon != "":
        try:
            our_icon = join("art", icon)
            if exists(our_icon):
                pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(our_icon, width, height)
            elif icon.startswith("/"):
                pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(icon, width, height)
            else:
                pixbuf = ICON_THEME.load_icon(splitext(icon)[0], width, gtk.ICON_LOOKUP_USE_BUILTIN)
            except Exception, msg1:
            try:
                pixbuf = ICON_THEME.load_icon(icon, width, gtk.ICON_LOOKUP_USE_BUILTIN)
            except Exception, msg2:
                print 'Error:load_icon:Icon Load Error:%s (or %s)' % (msg1, msg2)

    # an icon that is too tall will make the EntryCompletion look funny
    if pixbuf != None and pixbuf.get_height() > height:
        pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
    return pixbuf
