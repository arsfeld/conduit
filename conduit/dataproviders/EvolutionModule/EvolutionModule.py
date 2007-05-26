try:
    import evolution as evo

    MODULES = {
    	"EvoContactSource" : { "type": "dataprovider" }	
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

MODULES = {
	"EvoContactSource" : { "type": "dataprovider" }	
}

class EvoContactSource(DataProvider.DataSource):

    DEFAULT_ADDRESSBOOK = "default"

    _name_ = "Evolution Contacts"
    _description_ = "Sync your Contacts"
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.contacts = None

        self.selectedAddressBook = EvoContactSource.DEFAULT_ADDRESSBOOK

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



#        cb = gtk.combo_box_new_text()
#        for displayname,  in self._addressBooks:
#            cb.append_text(b)

#        vbox.pack_end(c)
#        cb.show()
        
        #preload the widgets
        #if self.limit > 0:
        #    limitCb.set_active(True)
        #    limitSb.set_value(self.limit)
        #else:
        #    limitCb.set_active(False)
        #url.set_text(self.feedUrl)
        #photosCb.set_active(self.downloadPhotos)
        #audioCb.set_active(self.downloadAudio)
        
        dlg = tree.get_widget("ContactConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            pass

        dlg.destroy()            

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.contacts = []

        book = evo.open_addressbook('default')
        for i in book.get_all_contacts():
            contact = Contact.Contact(None)
            contact.set_from_vcard_string(i.get_vcard_string())
            contact.set_UID(i.get_uid())

            self.contacts.append(contact)

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return self.contacts[index]

    def finish(self):
        DataProvider.DataSource.finish(self)
        self.contacts = None

    def get_configuration(self):
        return {
            "selectedAddressBook" : self.selectedAddressBook
            }

    def set_configuration(self, config):
        self.selectedAddressBook = config.get("selectedAddressBook", EvoContactSource.DEFAULT_ADDRESSBOOK)

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return self.selectedAddressBook
