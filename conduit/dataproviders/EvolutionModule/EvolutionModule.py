MODULES = {}
try:
    import evolution as evo
    if evo.__version__ == (0,0,1):
        MODULES = {
        	"EvoContactTwoWay" : { "type": "dataprovider" }	
        }
except ImportError: pass
    

import gtk
import gobject

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.datatypes.Contact as Contact
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import datetime

class EvoContactTwoWay(DataProvider.TwoWay):

    DEFAULT_ADDRESSBOOK = "default"

    _name_ = "Evolution Contacts"
    _description_ = "Sync your Contacts"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.contacts = None

        self.selectedAddressBook = EvoContactTwoWay.DEFAULT_ADDRESSBOOK
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
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "ContactConfigDialog"
                        )
        
        #get a whole bunch of widgets
        bookComboBox = tree.get_widget("bookComboBox")

        #make a combobox with the addressbooks
        store = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        bookComboBox.set_model(store)

        cell = gtk.CellRendererText()
        bookComboBox.pack_start(cell, True)
        bookComboBox.add_attribute(cell, 'text', 0)

        for name,id in self._addressBooks:
            rowref = store.append( (name, id) )
            if id == self.selectedAddressBook:
                bookComboBox.set_active_iter(rowref)
        
        dlg = tree.get_widget("ContactConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            pass

        dlg.destroy()            

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.contacts = []

        self.book = evo.open_addressbook(self.selectedAddressBook)
        for i in self.book.get_all_contacts():
            self.contacts.append(i.get_uid())

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        uid = self.contacts[index]
        return self._get_contact(uid)

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
                        raise Exceptions.SynchronizeConflictError(comp, contact, existingContact)
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
            "selectedAddressBook" : self.selectedAddressBook
            }

    def set_configuration(self, config):
        self.selectedAddressBook = config.get("selectedAddressBook", EvoContactTwoWay.DEFAULT_ADDRESSBOOK)

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return self.selectedAddressBook
