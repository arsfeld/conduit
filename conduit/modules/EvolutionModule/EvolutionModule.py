from gettext import gettext as _

MODULES = {}
try:
    import evolution
    if evolution.__version__ >= (0,0,4):
        MODULES = {
                "EvoContactTwoWay"  : { "type": "dataprovider" },
                "EvoCalendarTwoWay" : { "type": "dataprovider" },
                "EvoTasksTwoWay"    : { "type": "dataprovider" },
                "EvoMemoTwoWay"     : { "type": "dataprovider" },
        }
except:
    pass
    
import datetime
import gobject
import logging
log = logging.getLogger("modules.Evolution")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Note as Note

class EvoBase(DataProvider.TwoWay):
    def __init__(self, sourceURI, *args):
        DataProvider.TwoWay.__init__(self)
        self.defaultURI = sourceURI
        self.sourceURI = sourceURI
        self.uids = None

    def _get_object(self, uid):
        raise NotImplementedError

    def _create_object(self, obj):
        raise NotImplementedError

    def _update_object(self, uid, obj):
        if self._delete_object(uid):
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
                    rid = self._update_object(LUID, obj)
                    return rid
                else:
                    comp = obj.compare(existing)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, existing, obj)
                    else:
                        # overwrite and return new ID
                        rid = self._update_object(LUID, obj)
                        return rid

        # if we get here then it is new...
        log.info("Creating new object")
        rid = self._create_object(obj)
        return rid

    def delete(self, LUID):
        if not self._delete_object(LUID):
            log.warn("Error deleting event (uid: %s)" % LUID)

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        self.uids = None

    def configure(self, window, selected, sources, name):
        import gtk
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "EvolutionConfigDialog"
                        )
        
        #get a whole bunch of widgets
        sourceComboBox = tree.get_widget("sourceComboBox")
        sourceLabel = tree.get_widget("sourceLabel")
        sourceLabel.set_text(_("Select %s:") % name)

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
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
            selected = store.get_value(sourceComboBox.get_active_iter(), 1)

        dlg.destroy()  
        return selected

    def get_configuration(self):
        return {
            "sourceURI" : self.sourceURI
            }

    def set_configuration(self, config):
        self.sourceURI = config.get("sourceURI", self.defaultURI)

    def get_UID(self):
        return self.sourceURI


class EvoContactTwoWay(EvoBase):

    DEFAULT_ADDRESSBOOK_URI = "default"

    _name_ = _("Evolution Contacts")
    _description_ = _("Sync your contacts")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoContactTwoWay.DEFAULT_ADDRESSBOOK_URI)
        self._addressBooks = evolution.ebook.list_addressbooks()

    def _get_object(self, LUID):
        """
        Retrieve a specific contact object from evolution
        """
        obj = self.book.get_contact(LUID)
        contact = Contact.Contact(None)
        contact.set_from_vcard_string(obj.get_vcard_string())
        contact.set_UID(obj.get_uid())
        contact.set_mtime(datetime.datetime.fromtimestamp(obj.get_modified()))
        return contact

    def _create_object(self, contact):
        obj = evolution.ebook.EContact(vcard=contact.get_vcard_string())
        if self.book.add_contact(obj):
            mtime = datetime.datetime.fromtimestamp(obj.get_modified())
            return Rid(uid=obj.get_uid(), mtime=mtime, hash=mtime)
        else:
            raise Exceptions.SyncronizeError("Error creating contact")

    def _delete_object(self, uid):
        try:
            return self.book.remove_contact_by_id(uid)
        except:
            # sys.excepthook(*sys.exc_info())
            return False

    def refresh(self):
        EvoBase.refresh(self)
        
        self.book = evolution.ebook.open_addressbook(self.sourceURI)
        for i in self.book.get_all_contacts():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.sourceURI = EvoBase.configure(self, 
                                    window, 
                                    self.sourceURI, 
                                    self._addressBooks,
                                    "Addressbook"
                                    )

class EvoCalendarTwoWay(EvoBase):

    DEFAULT_CALENDAR_URI = "default"

    _name_ = _("Evolution Calendar")
    _description_ = _("Sync your calendar")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoCalendarTwoWay.DEFAULT_CALENDAR_URI)
        self._calendarURIs = evolution.ecal.list_calendars()

    def _get_object(self, LUID):
        """
        Get an event from Evolution.
        """
        raw = self.calendar.get_object(LUID, "")
        event = Event.Event(None)
        event.set_from_ical_string(self.calendar.get_object_as_string(raw))
        event.set_UID(raw.get_uid())
        event.set_mtime(datetime.datetime.fromtimestamp(raw.get_modified()))
        return event

    def _create_object(self, event):
        # work around.. (avoid duplicate UIDs)
        if "UID" in [x.name for x in list(event.iCal.lines())]:
            event.iCal.remove(event.iCal.uid)

        obj = evolution.ecal.ECalComponent(evolution.ecal.CAL_COMPONENT_EVENT, event.get_ical_string())
        if self.calendar.add_object(obj):
            mtime = datetime.datetime.fromtimestamp(obj.get_modified())
            return Rid(uid=obj.get_uid(), mtime=mtime, hash=mtime)
        else:
            raise Exceptions.SyncronizeError("Error creating event")

    def _delete_object(self, uid):
        try:
            return self.calendar.remove_object(self.calendar.get_object(uid, ""))
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        
        self.calendar = evolution.ecal.open_calendar_source(
                            self.sourceURI, 
                            evolution.ecal.CAL_SOURCE_TYPE_EVENT
                            )
        for i in self.calendar.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.sourceURI = EvoBase.configure(self, 
                                    window, 
                                    self.sourceURI, 
                                    self._calendarURIs,
                                    "Calendar"
                                    )

class EvoTasksTwoWay(EvoBase):

    DEFAULT_TASK_URI = "default"

    _name_ = _("Evolution Tasks")
    _description_ = _("Sync your tasks")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "tomboy"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoTasksTwoWay.DEFAULT_TASK_URI)
        self._uris = evolution.ecal.list_task_sources()

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

        obj = evolution.ecal.ECalComponent(
                    evolution.ecal.CAL_COMPONENT_TODO, 
                    event.get_ical_string()
                    )
        if self.tasks.add_object(obj):
            mtime = datetime.datetime.fromtimestamp(obj.get_modified())
            return Rid(uid=obj.get_uid(), mtime=mtime, hash=mtime)
        else:
            raise Exceptions.SyncronizeError("Error creating event")

    def _delete_object(self, uid):
        try:
            return self.tasks.remove_object(self.tasks.get_object(uid, ""))
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        self.tasks = evolution.ecal.open_calendar_source(
                        self.sourceURI, 
                        evolution.ecal.CAL_SOURCE_TYPE_TODO
                        )
        for i in self.tasks.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.sourceURI = EvoBase.configure(self, 
                                    window, 
                                    self.sourceURI, 
                                    self._uris,
                                    "Tasks"
                                    )

class EvoMemoTwoWay(EvoBase):

    DEFAULT_MEMO_URI = ""

    _name_ = _("Evolution Memos")
    _description_ = _("Sync your memos")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoMemoTwoWay.DEFAULT_MEMO_URI)
        self.source = None
        self._memoSources = evolution.ecal.list_memo_sources()

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

        if note.contents == None:
            note.contents = ""

        note.set_UID(obj.get_uid())
        note.set_mtime(mtime)
        print note.get_note_string()
        return note

    def _create_object(self, note):
        obj = evolution.ecal.ECalComponent(evolution.ecal.CAL_COMPONENT_JOURNAL)
        obj.set_summary(note.title)
        if note.contents != None:
            obj.set_description(note.contents)
        uid = self.source.add_object(obj)
        
        if uid != None:
            mtime = datetime.datetime.fromtimestamp(obj.get_modified())
            return Rid(uid=uid, mtime=mtime, hash=mtime)
        else:
            raise Exceptions.SyncronizeError("Error creating memo")

    def _delete_object(self, uid):
        try:
            return self.source.remove_object(self.source.get_object(uid, ""))
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        self.source = evolution.ecal.open_calendar_source(
                        self.sourceURI, 
                        evolution.ecal.CAL_SOURCE_TYPE_JOURNAL
                        )
        for i in self.source.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        self.sourceURI = EvoBase.configure(self, 
                                    window, 
                                    self.sourceURI, 
                                    self._memoSources,
                                    "Memo Source"
                                    )


