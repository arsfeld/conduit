import gtk.gdk
import colorsys

#
# Tango colors taken from 
# http://tango.freedesktop.org/Tango_Icon_Theme_Guidelines
#
TANGO_COLOR_BUTTER_LIGHT = int("fce94fff",16)
TANGO_COLOR_BUTTER_MID = int("edd400ff",16)
TANGO_COLOR_BUTTER_DARK = int("c4a000ff",16)
TANGO_COLOR_ORANGE_LIGHT = int("fcaf3eff",16)
TANGO_COLOR_ORANGE_MID = int("f57900",16)
TANGO_COLOR_ORANGE_DARK = int("ce5c00ff",16)
TANGO_COLOR_CHOCOLATE_LIGHT = int("e9b96eff",16)
TANGO_COLOR_CHOCOLATE_MID = int("c17d11ff",16)
TANGO_COLOR_CHOCOLATE_DARK = int("8f5902ff",16)
TANGO_COLOR_CHAMELEON_LIGHT = int("8ae234ff",16)
TANGO_COLOR_CHAMELEON_MID = int("73d216ff",16)
TANGO_COLOR_CHAMELEON_DARK = int("4e9a06ff",16)
TANGO_COLOR_SKYBLUE_LIGHT = int("729fcfff",16)
TANGO_COLOR_SKYBLUE_MID = int("3465a4ff",16)
TANGO_COLOR_SKYBLUE_DARK = int("204a87ff",16)
TANGO_COLOR_PLUM_LIGHT = int("ad7fa8ff",16)
TANGO_COLOR_PLUM_MID = int("75507bff",16)
TANGO_COLOR_PLUM_DARK = int("5c3566ff",16)
TANGO_COLOR_SCARLETRED_LIGHT = int("ef2929ff",16)
TANGO_COLOR_SCARLETRED_MID = int("cc0000ff",16)
TANGO_COLOR_SCARLETRED_DARK = int("a40000ff",16)
TANGO_COLOR_ALUMINIUM1_LIGHT = int("eeeeecff",16)
TANGO_COLOR_ALUMINIUM1_MID = int("d3d7cfff",16)
TANGO_COLOR_ALUMINIUM1_DARK = int("babdb6ff",16)
TANGO_COLOR_ALUMINIUM2_LIGHT = int("888a85ff",16)
TANGO_COLOR_ALUMINIUM2_MID = int("555753ff",16)
TANGO_COLOR_ALUMINIUM2_DARK = int("2e3436ff",16)
TRANSPARENT_COLOR = int("00000000",16)

#
# Color conversion utility functions
#
def str2gdk(name):
    return gtk.gdk.color_parse(name)

def int2gdk(i):
    red   = (i >> 24) & 0xff
    green = (i >> 16) & 0xff
    blue  = (i >>  8) & 0xff
    return gtk.gdk.Color(red * 256, green * 256, blue * 256)

def gdk2intrgba(color, a=0xff):
    return (color.red   / 256 << 24) \
         | (color.green / 256 << 16) \
         | (color.blue  / 256 <<  8) \
         | 0xff
         
def gdk2intrgb(color):
    return (color.red   / 256 << 16) \
         | (color.green / 256 << 8) \
         | (color.blue  / 256 )

def gdk2rgb(color):
    return (color.red / 65535.0, color.green / 65535.0, color.blue / 65535.0)

def gdk2rgba(color, a=1):
    return (color.red / 65535.0, color.green / 65535.0, color.blue / 65535.0, a)

def rgba2int(r, g, b, a):
    return gdk2intrgba(gtk.gdk.Color(r, g, b))

def convert(color, converter):
    if isinstance(color, gtk.gdk.Color):
        pass
    elif type(color) == type(0) or type(color) == type(0l):
        color = int2gdk(color)
    elif type(color) == type(''):
        color = str2gdk(color)
    else:
        raise TypeError('%s is not a known color type' % type(color))
    return converter(color)

def to_int(color):
    return convert(color, gdk2int)

def to_rgb(color):
    return convert(color, gdk2rgb)

def to_rgba(color):
    return convert(color, gdk2rgba)

def shade_color_rgb(color_rgb, ratio):
    #color_rgb = [c / float(255) for c in color_rgb]
    #log.debug(color_rgb)
    h, l, s = colorsys.rgb_to_hls(*color_rgb)             
    l = max(min(l * ratio, 1), 0);
    s = max(min(s * ratio, 1), 0);
    #log.debug(colorsys.hls_to_rgb(h, l, s))
    return colorsys.hls_to_rgb(h, l, s)

def shade_color(color, ratio):
    r, g, b = shade_color_rgb(gdk2rgb(color))
    return gtk.gdk.Color(r * 65535, g * 65535, b * 65535)

def rgba2int(r, g, b, a = 1.0):
    return gdk2intrgba(gtk.gdk.Color(r * 65535, g * 65535, b * 65535), a * 65535)

def rgb_to_int(r, g, b):
    return (r  / 256 << 24) \
            | (g  / 256 << 16) \
            | (b  / 256 <<  8) \
            | 0xff
