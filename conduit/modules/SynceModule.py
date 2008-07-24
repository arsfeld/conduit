import conduit
import conduit.utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.HalFactory as HalFactory
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact
import conduit.Exceptions as Exceptions

import xml.dom.minidom
import vobject

import logging
log = logging.getLogger("modules.SynCE")

import os.path
import traceback
import dbus
import threading
import gobject
import array

from gettext import gettext as _

SYNC_ITEM_CALENDAR  = 0
SYNC_ITEM_CONTACTS  = 1
SYNC_ITEM_EMAIL     = 2
SYNC_ITEM_FAVORITES = 3
SYNC_ITEM_FILES     = 4
SYNC_ITEM_MEDIA     = 5
SYNC_ITEM_NOTES     = 6
SYNC_ITEM_TASKS     = 7

TYPETONAMES = {
    SYNC_ITEM_CONTACTS  : "Contacts",
    SYNC_ITEM_CALENDAR  : "Calendar",
    SYNC_ITEM_TASKS     : "Tasks"
}

CHANGE_ADDED        = 1
CHANGE_MODIFIED     = 4
CHANGE_DELETED      = 3

MODULES = {
    "SynceFactory" :        { "type": "dataprovider-factory" },
}

class SynceFactory(HalFactory.HalFactory):

    SUPPORTED_PARTNERSHIPS = ("Calendar", "Contacts", "Tasks")

    def __init__(self, **kwargs):
        HalFactory.HalFactory.__init__(self, **kwargs)
        self._found = False
        self._item_types = {}
        self._partnerships = []
        
    def _get_item_types_rx(self, item_types):
        self._item_types = item_types

    def _get_partnerships_rx(self, partnerships):  
        self._partnerships = partnerships
        
    def _create_partnership_rx(self, guid):
        print args
        
    def _create_partnership_error(self, e):
    	log.warn("Failed to create partnership: %s" % e._dbus_error_name)
        
    def _on_create_partnership_clicked(self, sender, mod):
        #create partnerships for Contact, Calendar, Tasks
        ids = [id for id, name in self._item_types.items() if str(name) in self.SUPPORTED_PARTNERSHIPS]
        self.engine.CreatePartnership(
                            "Conduit",      #partnership name
                            ids,            #ids of those items to sync
            	            reply_handler=self._create_partnership_rx,
            	            error_handler=self._create_partnership_error
            	            )
        
    def _found_device(self):
        self._found = True
        
        #call async so we dont block at startup
        #reply_handler will be called with the method's return values as arguments; or
        #the error_handler
        self.engine = dbus.Interface(
                    dbus.SessionBus().get_object('org.synce.SyncEngine', '/org/synce/SyncEngine'),
                    'org.synce.SyncEngine'
                    )
    	self.engine.GetItemTypes(
    	            reply_handler=self._get_item_types_rx,
    	            error_handler=lambda *args: None
    	            )
        self.engine.GetPartnerships(
    	            reply_handler=self._get_partnerships_rx,
    	            error_handler=lambda *args: None
    	            )

    def is_interesting(self, device, props):
        if props.has_key("sync.plugin") and props["sync.plugin"]=="synce":
            self._found_device()        
            return True
        return False

    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    "Windows Mobile",
                    "windows",
                    udi)

    def get_dataproviders(self, udi, **kwargs):
        return [SynceContactsTwoWay, SynceCalendarTwoWay, SynceTasksTwoWay]
        
    def setup_configuration_widget(self):
    
        if self._found:
            import gtk
            import socket
            
            vbox = gtk.VBox(False,5)
            mod = gtk.ListStore(
                            gobject.TYPE_PYOBJECT,      #parnership id
                            gobject.TYPE_PYOBJECT,      #parnership guid
                            str,str,str)                #device name, pc name, items
            treeview = gtk.TreeView(mod)
            
            #Three colums: device name, pc name, items
            index = 2
            for name in ("Device", "Computer", "Items to Synchronize"):
                col = gtk.TreeViewColumn(
                                    name, 
                                    gtk.CellRendererText(),
                                    text=index)
                treeview.append_column(col)
                index = index + 1
            vbox.pack_start(treeview,True,True)

            btn = gtk.Button(None,gtk.STOCK_ADD)
            btn.set_label("Create Partnership")
            btn.connect("clicked", self._on_create_partnership_clicked, mod)
            vbox.pack_start(btn, False, False)

            #add the existing partnerships
            for id,guid,name,hostname,devicename,storetype,items in self._partnerships:
                mod.append((
                        id,
                        guid,
                        str(devicename),
                        str(hostname),
                        ", ".join([str(self._item_types[item]) for item in items]))
                        )
                #disable partnership if one exists
                if str(hostname) == socket.gethostname():
                    btn.set_sensitive(False)
                    
            return vbox
        return None

    def save_configuration(self, ok):
        pass

class SyncEngineWrapper(object):
    """
    Wrap the SyncEngine dbus foo (thinly)
      Make it synchronous and (eventually) borg it so multiple dp's share one connection
    """

    def __init__(self):
        self.engine = None
        self.SyncEvent = threading.Event()
        self.PrefillEvent = threading.Event()

    def _OnSynchronized(self):
        log.info("Synchronize: Got _OnSynchronized")
        self.SyncEvent.set()

    def _OnPrefillComplete(self):
        log.info("Synchronize: Got _OnPrefillComplete")
        self.PrefillEvent.set()

    def Connect(self):
        if not self.engine:
            self.bus = dbus.SessionBus()
            proxy = self.bus.get_object("org.synce.SyncEngine", "/org/synce/SyncEngine")
            self.engine = dbus.Interface(proxy, "org.synce.SyncEngine")
            self.engine.connect_to_signal("Synchronized", lambda: gobject.idle_add(self._OnSynchronized))
            self.engine.connect_to_signal("PrefillComplete", lambda: gobject.idle_add(self._OnPrefillComplete))

    def Prefill(self, items):
        self.PrefillEvent.clear()
        rc = self.engine.PrefillRemote(items)
        if rc == 1:
            self.PrefillEvent.wait(10)
        log.info("Prefill: completed (rc=%d)" % rc)
        return rc

    def Synchronize(self):
        self.SyncEvent.clear()
        self.engine.Synchronize()
        self.SyncEvent.wait(10)
        log.info("Synchronize: completed")

    def GetRemoteChanges(self, type_ids):
        return self.engine.GetRemoteChanges(type_ids)

    def AcknowledgeRemoteChanges(self, acks):
        self.engine.AcknowledgeRemoteChanges(acks)

    def AddLocalChanges(self, chgset):
        self.engine.AddLocalChanges(chgset)

    def FlushItemDB(self):
        self.engine.FlushItemDB()

    def Disconnect(self):
        self.engine = None

class SynceTwoWay(DataProvider.TwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.objects = {}

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.engine = SyncEngineWrapper()
        self.engine.Connect()
        self.engine.Synchronize()

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        self.objects = {}
        self.engine.Prefill([TYPETONAMES[self._type_id_]])
        chgs = self.engine.GetRemoteChanges([self._type_id_])
        for guid, chgtype, data in chgs[self._type_id_]:
            uid = array.array('B', guid).tostring()
            blob = array.array('B', data).tostring()
            self.objects[uid] = self._blob_to_data(uid, blob)

        log.info("Got %s objects" % len(self.objects))
        return self.objects.keys()

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self.objects[LUID]

    def put(self, obj, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)
        existing = None
        if LUID != None:
            existing = self.get(LUID)
        if existing != None:
            comp = obj.compare(existing)
            if comp == conduit.datatypes.COMPARISON_EQUAL:
                log.info("objects are equal")
            elif overwrite == True or comp == conduit.datatypes.COMPARISON_NEWER:
                self.update(LUID, obj)
            else:
                raise Exceptions.SynchronizeConflictError(comp, obj, existing)
        else:
            LUID = self.add(obj)
        return self.get(LUID).get_rid()

    def _commit(self, uid, chgtype, blob):
        _uid = array.array('B')
        _uid.fromstring(uid)
        _blob = array.array('B')
        _blob.fromstring(blob)
        self.engine.AddLocalChanges({
            self._type_id_: (
                (_uid, chgtype, _blob),
            )
        })
        # FIXME: This is a HACK to make it easy (ish) to return a RID in put()
        if chgtype != CHANGE_DELETED:
            self.objects[uid] = self._blob_to_data(uid,blob)
        else:
            del self.objects[uid]

    def add(self, obj):
        LUID = Utils.uuid_string()
        self._commit(LUID, CHANGE_ADDED, self._data_to_blob(obj))
        return LUID

    def update(self, LUID, obj):
        self._commit(LUID, CHANGE_MODIFIED, self._data_to_blob(obj))

    def delete(self, LUID):
        DataProvider.TwoWay.delete(self,LUID)
        self._commit(LUID, CHANGE_DELETED, "")

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        #self.engine.AcknowledgeRemoteChanges
        self.engine.Synchronize()
        self.engine.FlushItemDB()

    def _blob_to_data(self, uid, blob):
        #raise NotImplementedError
        d = Note.Note(uid, blob)
        d.set_UID(uid)
        return d

    def _data_to_blob(self, data):
        #raise NotImplementedError
        return data.get_contents()

    def get_UID(self):
        return "synce-%d" % self._type_id_

class SynceContactsTwoWay(SynceTwoWay):
    _name_ = "Contacts"
    _description_ = "Windows Mobile Contacts"
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_CONTACTS
    _configurable_ = False

    def _blob_to_data(self, uid, blob):
        parser = xml.dom.minidom.parseString(blob)
        root = parser.getElementsByTagName("contact")[0]

        c = Contact.Contact()
        c.set_UID(uid)

        def S(node):
            if node and node[0].childNodes:
                return node[0].firstChild.wholeText
            return ""

        for node in root.childNodes:
            if node.nodeName == "FileAs":
                pass
            elif node.nodeName == "FormattedName":
                try:
		    c.vcard.fn
		except:
		    c.vcard.add('fn')
		c.vcard.fn.value = S(node.getElementsByTagName('Content'))
            elif node.nodeName == "Name":
                family = S(node.getElementsByTagName('LastName'))
                given = S(node.getElementsByTagName('FirstName'))
                try:
                    c.vcard.n
                except:
                    c.vcard.add('n')
                c.vcard.n.value = vobject.vcard.Name(family=family, given=given)
            elif node.nodeName == "Nickname":
                pass
            elif node.nodeName == "EMail":
                email = c.vcard.add('email')
                email.value = S(node.getElementsByTagName('Content'))
                email.type_param = 'INTERNET'
            elif node.nodeName == "Photo":
                pass
            elif node.nodeName == "Categories":
                pass
            elif node.nodeName == "Assistant":
                pass
            elif node.nodeName == "Manager":
                pass
            elif node.nodeName == "Organization":
                pass
            elif node.nodeName == "Spouse":
                pass
            elif node.nodeName == "Telephone":
	        tel = c.vcard.add('tel')
		tel.value = S(node.getElementsByTagName('Content'))
	        for type_param in node.getElementsByTagName('Type'):
		    tel.params.setdefault('TYPE',[]).append(S([type_param]))
            elif node.nodeName == "Title":
                pass
            elif node.nodeName == "Url":
                pass
            elif node.nodeName == "Uid":
                pass
            elif node.nodeName == "Revision":
                pass
            else:
                log.warning("Unhandled node: %s" % node.nodeName)

        return c

    def _data_to_blob(self, data):
      v = data.vcard
      doc = xml.dom.minidom.Document()
      node = doc.createElement("contact")
      for chunk, value in v.contents.iteritems():
          if chunk == "account":
              pass
          elif chunk == "tel":
              for v in value:
                  t = doc.createElement("Telephone")
		  if 'TYPE' in v.params:
		      for type_param in v.params['TYPE']:
		          k = doc.createElement("Type")
                          k.appendChild(doc.createTextNode(type_param))
                          t.appendChild(k)
                  c = doc.createElement("Content")
                  c.appendChild(doc.createTextNode(v.value))
                  t.appendChild(c)
                  node.appendChild(t)
          elif chunk == "bday":
              pass
          elif chunk == "n":
              v = value[0]
              n = doc.createElement("Name")
              f = doc.createElement("FirstName")
              f.appendChild(doc.createTextNode(v.value.given))
              n.appendChild(f)
              l = doc.createElement("LastName")
              l.appendChild(doc.createTextNode(v.value.family))
              n.appendChild(l)
              a = doc.createElement("Additional")
              n.appendChild(a)
              p = doc.createElement("Prefix")
              n.appendChild(p)
              s = doc.createElement("Suffix")
              n.appendChild(s)
              node.appendChild(n)
          elif chunk == "version":
              pass
          elif chunk == "org":
              pass
          elif chunk == "nickname":
              pass
          elif chunk == "email":
              for v in value:
                  e = doc.createElement("EMail")
                  c = doc.createElement("Content")
                  c.appendChild(doc.createTextNode(v.value))
                  e.appendChild(c)
                  n.appendChild(e)
          elif chunk == "fn":
              v = value[0]
              fn = doc.createElement("FormattedName")
              c = doc.createElement("Content")
              c.appendChild(doc.createTextNode(v.value))
              fn.appendChild(c)
              node.appendChild(fn)
          else:
              log.warning("Unhandled chunk (%s)" % chunk)

      doc.appendChild(node)
      return doc.toxml()

class SynceCalendarTwoWay(SynceTwoWay):
    _name_ = "Calendar"
    _description_ = "Windows Mobile Calendar"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_CALENDAR
    _configurable_ = False

class SynceTasksTwoWay(SynceTwoWay):
    _name_ = "Tasks"
    _description_ = "Windows Mobile Tasks"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_TASKS
    _configurable_ = False

