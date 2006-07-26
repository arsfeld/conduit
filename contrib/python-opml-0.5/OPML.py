""" OPML.py

"""

__copyright__ = "Copyright (c) 2002-2005 Free Software Foundation, Inc."
__author__  = "Juri Pakaste <juri@iki.fi>"
__license__ = """
Straw is free software; you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

Straw is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc., 59 Temple
Place - Suite 330, Boston, MA 02111-1307, USA. """


from xml.sax import saxutils, make_parser, SAXParseException
from xml.sax.handler import feature_namespaces, feature_namespace_prefixes
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
import xml.sax._exceptions
import xml.sax.handler
import sys

class BlogListEntry(object):
    __slots__ = ('text', 'url')

class OPML(dict):
    def __init__(self):
        self.outlines = []
    
    def output(self, stream = sys.stdout):
        xg = XMLGenerator(stream, encoding='utf-8')
        def elemWithContent(name, content):
            xg.startElement(name, AttributesImpl({}))
            if content is not None:
                xg.characters(content)
            xg.endElement(name)
            xg.characters("\n")
        xg.startElement("opml", AttributesImpl({'version': '1.1'}))
        xg.startElement("head", AttributesImpl({}))
        for key in ('title', 'dateCreated', 'dateModified', 'ownerName',
                    'ownerEmail', 'expansionState', 'vertScrollState',
                    'windowTop', 'windowBotton', 'windowRight', 'windowLeft'):
            if self.has_key(key) and self[key] != "":
                elemWithContent(key, self[key])
        xg.endElement("head")
        xg.startElement("body", AttributesImpl({}))
        for o in self.outlines:
            o.output(xg)
        xg.endElement("body")
        xg.endElement("opml")

class Outline(dict):
    __slots__ = ('_children')
    
    def __init__(self):
        self._children = []

    def add_child(self, outline):
        self._children.append(outline)

    def get_children_iter(self):
        return self.OIterator(self)

    children = property(get_children_iter, None, None, "")

    def output(self, xg):
        xg.startElement("outline", AttributesImpl(self))
        for c in self.children:
            c.output(xg)
        xg.endElement("outline")
        xg.characters("\n")

    class OIterator:
        def __init__(self, o):
            self._o = o
            self._index = -1

        def __iter__(self):
            return self

        def next(self):
            self._index += 1
            if self._index < len(self._o._children):
                return self._o._children[self._index]
            else:
                raise StopIteration

class OutlineList:
    def __init__(self):
        self._roots = []
        self._stack = []
    
    def add_outline(self, outline):
        if len(self._stack):
            self._stack[-1].add_child(outline)
        else:
            self._roots.append(outline)
        self._stack.append(outline)

    def close_outline(self):
        if len(self._stack):
            del self._stack[-1]

    def roots(self):
        return self._roots

class OPMLHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self._outlines = OutlineList()
        self._opml = None
        self._content = ""

    def startElement(self, name, attrs):
        if self._opml is None:
            if name != 'opml':
                raise ValueError, "This doesn't look like OPML"
            self._opml = OPML()
        if name == 'outline':
            o = Outline()
            o.update(attrs)
            self._outlines.add_outline(o)
        self._content = ""

    def endElement(self, name):
        if name == 'outline':
            self._outlines.close_outline()
            return
        if name == 'opml':
            self._opml.outlines = self._outlines.roots()
            return
        for key in ('title', 'dateCreated', 'dateModified', 'ownerName',
                    'ownerEmail', 'expansionState', 'vertScrollState',
                    'windowTop', 'windowBotton', 'windowRight', 'windowLeft'):
            if name == key:
                self._opml[key] = self._content
                return
        
    def characters(self, ch):
        self._content += ch

    def get_opml(self):
        return self._opml

def parse(stream):
    parser = make_parser()
    parser.setFeature(feature_namespaces, 0)
    handler = OPMLHandler()
    parser.setContentHandler(handler)

    parser.parse(stream)
    return handler.get_opml()

def _find_entries(outline):
    entries = []
    for c in outline.children:
        entries += _find_entries(c)
    type = outline.get('type', '')
    text = outline.get('text', '')
    e = None
    if type == 'link':
        url = outline.get('url', '')
        if url != '':
            e = BlogListEntry()
            e.text = text
            e.url = url
    else:
        xmlurl = outline.get('xmlUrl', '')
        e = BlogListEntry()
        e.text = text
        if text == '':
            title = outline.get('title', '')
            if title == '':
                e = None
            e.text = title
        if e != None:
            if xmlurl != '':
                # there's something in xmlurl. There's a good chance that's
                # our feed's URL
                e.url = xmlurl
            else:
                htmlurl = outline.get('htmlUrl', '')
                if htmlurl != '':
                    # there's something in htmlurl, and xmlurl is empty. This
                    # might be our feed's URL.
                    e.url = htmlurl
                else:
                    # nothing else to try.
                    e = None
    if e is not None:
        entries[0:0] = [e]
    return entries

def find_entries(outlines):
    entries = []
    for o in outlines:
        entries += _find_entries(o)
    return entries

def read(stream):
    try:
        o = parse(stream)
    except ValueError:
        return None
    entries = find_entries(o.outlines)
    ret = list()
    edict = dict()
    # avoid duplicates.
    for e in entries:
        ek = (e.text, e.url)
        edict[ek] = edict.get(ek, 0) + 1
        if edict[ek] < 2:
            ret.append(e)
    return ret

def import_opml(filename,category=None):
    fstream = open (filename)
    opml = read(fstream)
    if not opml:
        return
    for b in opml:
        print b
    return opml

