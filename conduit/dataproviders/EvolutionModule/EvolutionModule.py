MODULES = {}
try:
    import evolution as evo
    if evo.__version__ == (0,0,1):
        MODULES = {
        	"EvoContactTwoWay" : { "type": "dataprovider" },
        	"EvoMemoTwoWay" : { "type": "dataprovider" },
        }
except:
    pass
    

import gtk
import gobject

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Note as Note
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import datetime

class EvoBase:
    def __init__(self):
        pass

    def configure(self, window, selected, sources, name):
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "EvolutionConfigDialog"
                        )
        
        #get a whole bunch of widgets
        sourceComboBox = tree.get_widget("sourceComboBox")
        sourceLabel = tree.get_widget("sourceLabel")
        sourceLabel.set_text("Select %s:" % name)

        #make a combobox with the addressbooks
        store = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        sourceComboBox.set_model(store)

        cell = gtk.CellRendererText()
        sourceComboBox.pack_start(cell, True)
        sourceComboBox.add_attribute(cell, 'text', 0)
        sourceComboBox.set_active(0)
        
        for name,uri in sources:
            rowref = store.append( (name, uri) )
            if uri == selected:
                sourceComboBox.set_active_iter(rowref)
        
        dlg = tree.get_widget("EvolutionConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            selected = store.get_value(sourceComboBox.get_active_iter(), 1)

        dlg.destroy()  
        return selected

class EvoContactTwoWay(DataProvider.TwoWay, EvoBase):

    DEFAULT_ADDRESSBOOK_URI = "default"

    _name_ = "Evolution Contacts"
    _description_ = "Sync your Contacts"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        EvoBase.__init__(self)
        self.contacts = None

        self.addressBookURI = EvoContactTwoWay.DEFAULT_ADDRESSBOOK_URI
        self._addressBooks = evo.list_addressbooks()

    def _get_contact(self, LUID):
        """
        Retrieve a specific contact object from evolution
        FIXME: In 0.5 this will replace get(...)
        """
        obj = self.book.get_contact(LUID)
        contact = Contact.Contact(None)
        contact.set_from_vcard_string(obj.get_vcard_string())
        contact.set_UID(obj.get_uid())
        contact.set_mtime(datetime.datetime.fromtimestamp(obj.get_modified()))
        return contact

    def _create_contact(self, contact):
        obj = evo.EContact(vcard=contact.get_vcard_string())
        if self.book.add_contact(obj):
            return obj.get_uid()
        else:
            raise Exceptions.SyncronizeError("Error creating contact")

    def _delete_contact(self, uid):
        return self.book.remove_contact_by_id(uid)

    def _update_contact(self, uid, contact):
        if self._delete_contact(uid):
            uid = self._create_contact(contact)
            return uid
        else:
            raise Exceptions.SyncronizeError("Error updating contact (uid: %s)" % uid)

    def configure(self, window):
        self.addressBookURI = EvoBase.configure(self, 
                                    window, 
                                    self.addressBookURI, 
                                    self._addressBooks,
                                    "Addressbook"
                                    )

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.contacts = []

        self.book = evo.open_addressbook(self.addressBookURI)
        for i in self.book.get_all_contacts():
            self.contacts.append(i.get_uid())

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.contacts

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self._get_contact(LUID)

    def put(self, contact, overwrite, LUID=None):
        if LUID != None:
            obj = self.book.get_contact(LUID)
            if obj != None:
                if overwrite == True:
                    # overwrite and return new ID
                    uid = self._update_contact(LUID, contact)
                    return uid
                else:
                    existingContact = self._get_contact(LUID)
                    comp = contact.compare(existingContact)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, existingContact, contact)
                    else:
                        # overwrite and return new ID
                        uid = self._update_contact(LUID, contact)
                        return uid

        # if we get here then it is new...
        log("Creating new contact")
        uid = self._create_contact(contact)
        return uid

    def delete(self, LUID):
        if not self._delete_contact(LUID):
            logw("Error deleting contact (uid: %s)" % LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.contacts = None

    def get_configuration(self):
        return {
            "addressBookURI" : self.addressBookURI
            }

    def set_configuration(self, config):
        self.addressBookURI = config.get("addressBookURI", EvoContactTwoWay.DEFAULT_ADDRESSBOOK_URI)

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return self.addressBookURI

class EvoMemoTwoWay(DataProvider.TwoWay, EvoBase):

    DEFAULT_ADDRESSBOOK_URI = "default"

    _name_ = "Evolution Memos"
    _description_ = "Sync your Memos"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        EvoBase.__init__(self)
        self.source = None

        self.memoSourceURI = ""
        self._memoSources = evo.list_memo_sources()

    def _get_memo(self, LUID):
        """
        Retrieve a specific contact object from evolution
        FIXME: In 0.5 this will replace get(...)
        """
        obj = self.source.get_object(LUID, "")
        mtime = datetime.datetime.fromtimestamp(obj.get_modified())
        note = Note.Note(
                    title=obj.get_summary(),
                    mtime=mtime,
                    contents=obj.get_description()
                    )

        note.set_UID(obj.get_uid())
        note.set_mtime(mtime)
        print note.get_note_string()
        return note

    def _create_memo(self, note):
        obj = evo.ECalComponent(evo.CAL_COMPONENT_JOURNAL)
        obj.set_summary(note.title)
        obj.set_description(note.contents)
        uid = self.source.add_object(obj)
        
        if uid != None:
            return uid
        else:
            raise Exceptions.SyncronizeError("Error creating memo")

    def _delete_memo(self, uid):
        return self.source.remove_object(uid)

    def _update_memo(self, uid, memo):
        if self._delete_memo(uid):
            uid = self._create_memo(memo)
            return uid
        else:
            raise Exceptions.SyncronizeError("Error updating memo (uid: %s)" % uid)

    def configure(self, window):
        self.memoSourceURI = EvoBase.configure(self, 
                                    window, 
                                    self.memoSourceURI, 
                                    self._memoSources,
                                    "Memo Source"
                                    )

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.memos = []

        self.source = evo.open_calendar_source(self.memoSourceURI, evo.CAL_SOURCE_TYPE_JOURNAL)
        for i in self.source.get_all_objects():
            self.memos.append(i.get_uid())

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.memos

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self._get_memo(LUID)

    def put(self, memo, overwrite, LUID=None):
        if LUID != None:
            obj = self.source.get_object(LUID, "")
            if obj != None:
                if overwrite == True:
                    # overwrite and return new ID
                    uid = self._update_memo(LUID, memo)
                    return uid
                else:
                    existingMemo= self._get_memo(LUID)
                    comp = contact.compare(existingMemo)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, memo, existingMemo)
                    else:
                        # overwrite and return new ID
                        uid = self._update_memo(LUID, memo)
                        return uid

        # if we get here then it is new...
        log("Creating new memo")
        uid = self._create_memo(memo)
        return uid

    def delete(self, LUID):
        if not self._delete_memo(LUID):
            logw("Error deleting memo (uid: %s)" % LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.memos = None

    def get_configuration(self):
        return {
            "memoSourceURI" : self.memoSourceURI
            }

    def set_configuration(self, config):
        self.memoSourceURI = config.get("memoSourceURI", "")

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return self.memoSourceURI
