try:
    import evolution as evo

    MODULES = {
    	"EvoContactTwoWay" : { "type": "dataprovider" }	
    }
except ImportError:
    MODULES = {}

import gtk
import gobject

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.datatypes.Contact as Contact
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import datetime

class EvoContactTwoWay(DataProvider.DataSource):

    DEFAULT_ADDRESSBOOK = "default"

    _name_ = "Evolution Contacts"
    _description_ = "Sync your Contacts"
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.contacts = None

        self.selectedAddressBook = EvoContactTwoWay.DEFAULT_ADDRESSBOOK

        self._addressBooks = evo.list_addressbooks()

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
        DataProvider.DataSource.refresh(self)
        self.contacts = []

        self.book = evo.open_addressbook(self.selectedAddressBook)
        for i in self.book.get_all_contacts():
            self.contacts.append(i.get_uid())

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        uid = self.contacts[index]
        return self._get(uid)

    def _get(self, LUID):
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

    def put(self, contact, overwrite, LUID=None):
        if LUID != None:
            obj = self.book.get_contact(LUID)
            if obj != None:
                if overwrite == True:
                    # overwrite
                    # FIXME: Overwrite + return LUID instead of falling back to creating a new object
                    self.book.remove_contact_by_id(LUID)
                else:
                    existingContact = self._get(LUID)
                    comp = contact.compare(existingContact)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, contact, existingContact)
                    else:
                        # FIXME: Overwrite + return LUID instead of falling back to creating a new object
                        self.book.remove_contact_by_id(LUID)

        # if we get here then it is new...
        obj = evo.EContact(vcard=contact.get_vcard_string(), uid=LUID)
        self.book.add_contact(obj)
        return obj.get_uid()

    def delete(self, LUID):
        self.book.remove_contact_by_id(LUID)

    def finish(self):
        DataProvider.DataSource.finish(self)
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
