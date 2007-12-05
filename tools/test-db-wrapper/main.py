#!/usr/bin/env python

import sys
import os.path
import tempfile
import gtk
import gtk.glade
import pango
import random
import traceback
import thread
import getopt

import conduit
from conduit.Database import GenericDB,ThreadSafeGenericDB
from conduit.gtkui.Database import GenericDBListStore

class Tester(object):
    def __init__(self, table, db):
        self.table = table
        self.db = db
        gladeFile = os.path.join(os.path.dirname(__file__),"main.glade")
        widgets = gtk.glade.XML(gladeFile, "MainWindow")
        dic = { "add_clicked"       : self.on_add_clicked,
                "edit_clicked"      : self.on_edit_clicked,
                "delete_clicked"    : self.on_delete_clicked
                }
        widgets.signal_autoconnect(dic)
        window = widgets.get_widget("MainWindow")
        window.set_position(gtk.WIN_POS_CENTER)
        window.connect('destroy', self.on_quit)


        scroller = widgets.get_widget("scrolledwindow")
        self.treeview = gtk.TreeView()
        self.treeview.set_headers_visible(True)
        self.treeview.set_fixed_height_mode(True)
        scroller.add(self.treeview)

        index = 0
        for name in ('oid',) + tuple(self.db.get_fields(self.table)):
            column = gtk.TreeViewColumn()
            column.set_title(name)
            column.set_property('sizing', gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_property('min-width', 100)
            cell = gtk.CellRendererText()
            cell.set_property('single-paragraph-mode', True)
            column.pack_start(cell, False)
            column.add_attribute(cell, 'text', index)
            self.treeview.append_column(column)
            index = index + 1

        store = GenericDBListStore(self.table, self.db)
        self.treeview.set_model(store)

        window.show_all()
        gtk.main()
        
    def on_add_clicked(self, *args):
        self.db.insert(
                table=self.table,
                values=("a"+str(random.randint(0,10)),"b"+str(random.randint(0,10)),"c"+str(random.randint(0,10)), random.randint(1,1000))
                )
    
    def on_edit_clicked(self, *args):
        try:
            model, rowref = self.treeview.get_selection().get_selected()
            oid = model.get_value(rowref,0)
            self.db.update(
                        table=self.table,
                        oid=oid,
                        values=("d","e","f",0)
                        )
        except TypeError:
            print "ERROR EDITING"
            traceback.print_exc()

    def on_delete_clicked(self, *args):
        try:
            model, rowref = self.treeview.get_selection().get_selected()
            oid = model.get_value(rowref,0)
            self.db.delete(
                        table=self.table,
                        oid=oid
                        )
        except TypeError:
            print "ERROR DELETING"
            traceback.print_exc()

    def on_quit(self, *args):
        self.treeview.set_sensitive(False)
        self.treeview.set_model(None)
        gtk.main_quit()
        
if __name__ == '__main__':
    def usage():
        print "%s\nOptions:\n\t[--threaded]\n\t[--database=/path/to/test.db --table=entries]" % sys.argv[0]

    try:
        opts, args = getopt.getopt(sys.argv[1:], "td:n:h", ["threaded", "database=", "table=", "help"])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    threaded = False
    database = ""
    tableName = ""
    for o, a in opts:
        if o in ("-t", "--threaded"):
            threaded = True
        if o in ("-d", "--database"):
            database = os.path.abspath(a)
        if o in ("-n", "--table"):
            tableName = a
        if o in ("-h", "--help"):
            usage()
            sys.exit()

    if database == "":
        database = tempfile.mktemp()
        createDB = True
    else:
        if tableName == "":
            print "Please specify name of table in %s \n" % database
            usage()
            sys.exit(1)
        createDB = False

    if threaded:
        db = ThreadSafeGenericDB(database)
    else:
        db = GenericDB(database)

    #excercise some DB functions
    if createDB:
        for tableName in ("table1","table2"):
            print "###Create"
            db.create(
                table=tableName,
                fields=("foo","bar","baz","bob")
                )

            print "###Insert"
            for i in (1,2,3,4):
                db.insert(
                    table=tableName,
                    values=("a%s"%i,"b %s"%tableName,True, 10*i)
                    )
            db.insert(
                table=tableName,
                values=("d","e",False, 5000)
                )

            print "###Update"
            db.update(
                table=tableName,
                oid=2,
                values=("g","s",False, 0)
                )
            db.update(
                table=tableName,
                oid=1,
                foo="f",baz=True
                )

            print "###Delete"
            db.delete(
                table=tableName,
                oid=3
                )

            print "###SELECT"
            for foo,bar in db.select("SELECT foo,bar FROM %s WHERE bob = ?" % tableName, (40,)):
                print "\t%s,%s" % (foo,bar)

            for baz, in db.select("SELECT baz FROM %s WHERE bob = ?" % tableName, (40,)):
                print "\t%s" % type(baz)

            print "###SELECT ONE"
            foo,bar = db.select_one("SELECT foo,bar FROM %s WHERE bob = ?" % tableName, (0,))
            print "\t%s,%s" % (foo,bar)

            print "###SELECT NONE"
            none = db.select_one("SELECT oid FROM %s WHERE bob = -1" % tableName)
            print "\t%s" % none

            print "###SELECT COUNT"
            count, = db.select_one("SELECT COUNT(oid) FROM %s WHERE bob != ?" % tableName, (0,))
            print "\t=%s" % count
            
            print "###SELECT UNION"
            sql =   "SELECT foo,bar FROM %s WHERE oid = ? " \
                    "UNION " \
                    "SELECT baz,bar FROM %s WHERE oid = ? " \
                    "UNION " \
                    "SELECT foo,bar FROM %s WHERE oid = ?" % (tableName,tableName,tableName)
            for foo,bar in db.select(sql, (1,2,4)):
                print "\t%s,%s" % (foo,bar)

    test = Tester(tableName,db)
    db.close()

