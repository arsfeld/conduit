import datetime
import gobject
from gettext import gettext as _
import logging
log = logging.getLogger("modules.Evolution")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
import conduit.Exceptions as Exceptions
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Note as Note

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
        log.info("Module Information: %s" % Utils.get_module_information(evolution, '__version__'))
except ImportError:
    log.info("Evolution support disabled")

class EvoBase(DataProvider.TwoWay):
    _configurable_ = True
    def __init__(self, sourceURI, *args):
        DataProvider.TwoWay.__init__(self)
        self.defaultSourceURI = sourceURI
        self.selectedSourceURI = sourceURI
        self.allSourceURIs = []
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
                    comp = obj.compare(existing, "%s-%s" % (self.__class__.__name__, self.get_UID()))
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, obj, existing)
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

    def configure(self, window, name):
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
        
        for name,uri in self.allSourceURIs:
            rowref = store.append( (name, uri) )
            if uri == self.selectedSourceURI:
                sourceComboBox.set_active_iter(rowref)
        
        dlg = tree.get_widget("EvolutionConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.selectedSourceURI = store.get_value(sourceComboBox.get_active_iter(), 1)
        dlg.destroy()  

    def get_configuration(self):
        return {
            "sourceURI" : self.selectedSourceURI
            }

    def set_configuration(self, config):
        self.selectedSourceURI = config.get("sourceURI", self.defaultSourceURI)

    def get_UID(self):
        return self.selectedSourceURI


class EvoContactTwoWay(EvoBase):

    DEFAULT_ADDRESSBOOK_URI = "default"

    _name_ = _("Evolution Contacts")
    _description_ = _("Sync your contacts")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "x-office-address-book"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoContactTwoWay.DEFAULT_ADDRESSBOOK_URI)
        self.allSourceURIs = evolution.ebook.list_addressbooks()

    def _get_object(self, LUID):
        """
        Retrieve a specific contact object from evolution
        """
        obj = self.book.get_contact(LUID)
        contact = Contact.Contact()
        contact.set_from_vcard_string(obj.get_vcard_string())
        contact.set_UID(obj.get_uid())
        contact.set_mtime(datetime.datetime.fromtimestamp(obj.get_modified()))
        return contact

    def _create_object(self, contact):
        obj = evolution.ebook.EContact(vcard=contact.get_vcard_string())
        if self.book.add_contact(obj):
            return self._get_object(obj.get_uid()).get_rid()
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
        
        self.book = evolution.ebook.open_addressbook(self.selectedSourceURI)
        for i in self.book.get_all_contacts():
            self.uids.append(i.get_uid())

    def configure(self, window):
        EvoBase.configure(self, window, "Addressbook")

class EvoCalendarTwoWay(EvoBase):

    DEFAULT_CALENDAR_URI = "default"

    _name_ = _("Evolution Calendar")
    _description_ = _("Sync your calendar")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "x-office-calendar"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoCalendarTwoWay.DEFAULT_CALENDAR_URI)
        self.allSourceURIs = evolution.ecal.list_calendars()

    def _get_object(self, LUID):
        """
        Get an event from Evolution.
        """
        raw = self.calendar.get_object(LUID, "")
        event = Event.Event()
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
            return conduit.datatypes.Rid(uid=obj.get_uid(), mtime=mtime, hash=mtime)
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
                            self.selectedSourceURI, 
                            evolution.ecal.CAL_SOURCE_TYPE_EVENT
                            )
        for i in self.calendar.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        EvoBase.configure(self, window, "Calendar")

class EvoTasksTwoWay(EvoBase):

    DEFAULT_TASK_URI = "default"

    _name_ = _("Evolution Tasks")
    _description_ = _("Sync your tasks")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "evolution-tasks"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoTasksTwoWay.DEFAULT_TASK_URI)
        self.allSourceURIs = evolution.ecal.list_task_sources()

    def _get_object(self, LUID):
        raw = self.tasks.get_object(LUID, "")
        task = Event.Event()
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
            return conduit.datatypes.Rid(uid=obj.get_uid(), mtime=mtime, hash=mtime)
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
                        self.selectedSourceURI, 
                        evolution.ecal.CAL_SOURCE_TYPE_TODO
                        )
        for i in self.tasks.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        EvoBase.configure(self, window, "Tasks")

class EvoMemoTwoWay(EvoBase):

    DEFAULT_MEMO_URI = ""

    _name_ = _("Evolution Memos")
    _description_ = _("Sync your memos")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "evolution-memos"

    def __init__(self, *args):
        EvoBase.__init__(self, EvoMemoTwoWay.DEFAULT_MEMO_URI)
        self.allSourceURIs = evolution.ecal.list_memo_sources()

    def _get_object(self, LUID):
        """
        Retrieve a specific contact object from evolution
        FIXME: In 0.5 this will replace get(...)
        """	
        obj = self.memos.get_object(LUID, "")
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
        return note

    def _create_object(self, note):
        obj = evolution.ecal.ECalComponent(evolution.ecal.CAL_COMPONENT_JOURNAL)
        obj.set_summary(note.title)
        if note.contents != None:
            obj.set_description(note.contents)
        uid = self.memos.add_object(obj)
        
        if uid != None:
            mtime = datetime.datetime.fromtimestamp(obj.get_modified())
            note = self._get_object(uid)
            return note.get_rid()
        else:
            raise Exceptions.SyncronizeError("Error creating memo")

    def _delete_object(self, uid):
        try:
            return self.memos.remove_object(self.memos.get_object(uid, ""))
        except:
            return False

    def refresh(self):
        EvoBase.refresh(self)
        self.memos = evolution.ecal.open_calendar_source(
                        self.selectedSourceURI, 
                        evolution.ecal.CAL_SOURCE_TYPE_JOURNAL
                        )
        for i in self.memos.get_all_objects():
            self.uids.append(i.get_uid())

    def configure(self, window):
        EvoBase.configure(self, window, "Memos")

