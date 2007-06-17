MODULES = {}
try:
    import evolution as evo
    if evo.__version__ == (0,0,1):
        MODULES = {
                "EvoContactTwoWay"  : { "type": "dataprovider" },
                "EvoCalendarTwoWay" : { "type": "dataprovider" },
                "EvoTasksTwoWay"    : { "type": "dataprovider" },
                "EvoMemoTwoWay"     : { "type": "dataprovider" },
        }
except:
    pass
    

import gtk
import gobject

import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions

import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Note as Note

import datetime

class EvoBase(DataProvider.TwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.uids = None

    def _get_object(self, uid):
        raise NotImplementedError

    def _create_object(self, obj):
        raise NotImplementedError

    def _update_object(self, uid, obj):
        if self._delete_object(obj):
            uid = self._create_object(obj)
            return uid
        else:
            raise Exceptions.SyncronizeError("Error updating object (uid: %s)" % uid)

    def _delete_object(self, uid):
        raise NotImplementedError

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.uids = []

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.uids

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self._get_object(LUID)

    def put(self, obj, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)
        if LUID != None:
            existing = self._get_object(LUID)
            if existing != None:
                if overwrite == True:
                    uid = self._update_object(LUID, obj)
                    return uid
                else:
                    comp = obj.compare(existing)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, existing, obj)
                    else:
                        # overwrite and return new ID
                        uid = self._update_object(LUID, obj)
                        return uid

        # if we get here then it is new...
        log("Creating new object")
        uid = self._create_object(obj)
        return uid

    def delete(self, LUID):
        if not self._delete_object(LUID):
            logw("Error deleting event (uid: %s)" % LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.uids = None

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

class EvoContactTwoWay(EvoBase):

    DEFAULT_ADDRESSBOOK_URI = "default"

    _name_ = "Evolution Contacts"
    _description_ = "Sync your Contacts"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        EvoBase.__init__(self)
        self.addressBookURI = EvoContactTwoWay.DEFAULT_ADDRESSBOOK_URI
        self._addressBooks = evo.list_addressbooks()

    def _get_object(self, LUID):
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

    def _create_object(self, contact):
        obj = evo.EContact(vcard=contact.get_vcard_string())
        if self.book.add_contact(obj):
            return obj.get_uid()
        else:
            raise Exceptions.SyncronizeError("Error creating contact")

    def _delete_object(self, uid):
        try:
            return self.book.remove_contact_by_id(uid)
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        
        self.book = evo.open_addressbook(self.addressBookURI)
        for i in self.book.get_all_contacts():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.addressBookURI = EvoBase.configure(self, 
                                    window, 
                                    self.addressBookURI, 
                                    self._addressBooks,
                                    "Addressbook"
                                    )

    def get_configuration(self):
        return {
            "addressBookURI" : self.addressBookURI
            }

    def set_configuration(self, config):
        self.addressBookURI = config.get("addressBookURI", EvoContactTwoWay.DEFAULT_ADDRESSBOOK_URI)

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return self.addressBookURI

class EvoCalendarTwoWay(EvoBase):

    DEFAULT_CALENDAR_URI = "default"

    _name_ = "Evolution Calendar"
    _description_ = "Sync your Calendar"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"

    def __init__(self, *args):
        EvoBase.__init__(self)
        self.calendarURI = EvoCalendarTwoWay.DEFAULT_CALENDAR_URI
        self._calendarURIs = evo.list_calendars()

    def _get_object(self, LUID):
        """
        Get an event from Evolution.
        """
        raw = self.calendar.get_object(LUID, "")
        event = Event.Event(None)
        event.set_from_ical_string(raw.get_as_string())
        event.set_UID(raw.get_uid())
        event.set_mtime(datetime.datetime.fromtimestamp(raw.get_modified()))
        return event

    def _create_object(self, event):
        # work around.. (avoid duplicate UIDs)
        if "UID" in [x.name for x in list(event.iCal.lines())]:
            event.iCal.remove(event.iCal.uid)

        obj = evo.ECalComponent(evo.CAL_COMPONENT_EVENT, event.get_ical_string())
        if self.calendar.add_object(obj):
            return obj.get_uid()
        else:
            raise Exceptions.SyncronizeError("Error creating event")

    def _delete_object(self, uid):
        try:
            return self.calendar.remove_object(self.calendar.get_object(uid, ""))
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        
        self.calendar = evo.open_calendar_source(self.calendarURI, evo.CAL_SOURCE_TYPE_EVENT)
        for i in self.calendar.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.calendarURI = EvoBase.configure(self, 
                                    window, 
                                    self.calendarURI, 
                                    self._calendarURIs,
                                    "Calendar"
                                    )

    def get_configuration(self):
        return {
            "calendarURI" : self.calendarURI
            }

    def set_configuration(self, config):
        self.calendarURI = config.get("calendarURI", EvoCalendarTwoWay.DEFAULT_CALENDAR_URI)

    def get_UID(self):
        #return the uri of the evo calendar in use
        return self.calendarURI

class EvoTasksTwoWay(EvoBase):

    DEFAULT_URI = "default"

    _name_ = "Evolution Tasks"
    _description_ = "Sync your Tasks"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "tomboy"

    def __init__(self, *args):
        EvoBase.__init__(self)
        self.uri = self.DEFAULT_URI
        self._uris = evo.list_task_sources()

    def _get_object(self, LUID):
        raw = self.tasks.get_object(LUID, "")
        task = Event.Event(None)
        task.set_from_ical_string(raw.get_as_string())
        task.set_UID(raw.get_uid())
        task.set_mtime(datetime.datetime.fromtimestamp(raw.get_modified()))
        return task

    def _create_object(self, event):
        # work around.. (avoid duplicate UIDs)
        if "UID" in [x.name for x in list(event.iCal.lines())]:
            event.iCal.remove(event.iCal.uid)

        obj = evo.ECalComponent(evo.CAL_COMPONENT_TODO, event.get_ical_string())
        if self.tasks.add_object(obj):
            return obj.get_uid()
        else:
            raise Exceptions.SyncronizeError("Error creating event")

    def _delete_object(self, uid):
        try:
            return self.tasks.remove_object(self.tasks.get_object(uid, ""))
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        self.tasks = evo.open_calendar_source(self.uri, evo.CAL_SOURCE_TYPE_TODO)
        for i in self.tasks.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.uri = EvoBase.configure(self, 
                                    window, 
                                    self.uri, 
                                    self._uris,
                                    "Tasks"
                                    )

    def get_configuration(self):
        return {
            "tasksURI" : self.uri
            }

    def set_configuration(self, config):
        self.uri = config.get("tasksURI", self.DEFAULT_URI)

    def get_UID(self):
        #return the uri of the evo calendar in use
        return self.uri

class EvoMemoTwoWay(EvoBase):

    DEFAULT_ADDRESSBOOK_URI = "default"

    _name_ = "Evolution Memos"
    _description_ = "Sync your Memos"
    _category_ = DataProvider.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        EvoBase.__init__(self)
        self.source = None

        self.memoSourceURI = ""
        self._memoSources = evo.list_memo_sources()

    def _get_object(self, LUID):
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

    def _create_object(self, note):
        obj = evo.ECalComponent(evo.CAL_COMPONENT_JOURNAL)
        obj.set_summary(note.title)
        obj.set_description(note.contents)
        uid = self.source.add_object(obj)
        
        if uid != None:
            return uid
        else:
            raise Exceptions.SyncronizeError("Error creating memo")

    def _delete_object(self, uid):
        try:
            return self.source.remove_object(uid)
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        self.source = evo.open_calendar_source(self.memoSourceURI, evo.CAL_SOURCE_TYPE_JOURNAL)
        for i in self.source.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.memoSourceURI = EvoBase.configure(self, 
                                    window, 
                                    self.memoSourceURI, 
                                    self._memoSources,
                                    "Memo Source"
                                    )

    def get_configuration(self):
        return {
            "memoSourceURI" : self.memoSourceURI
            }

    def set_configuration(self, config):
        self.memoSourceURI = config.get("memoSourceURI", "")

    def get_UID(self):
        #return the uri of the evo addressbook in use
        return self.memoSourceURI
