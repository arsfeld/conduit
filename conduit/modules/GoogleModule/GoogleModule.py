import gobject
import datetime
import dateutil.parser
from dateutil.tz import tzutc, tzlocal
import logging
log = logging.getLogger("modules.Google")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Event as Event

try:
    import vobject
    import gdata.calendar.service
    import gdata.service
    import gdata.calendar
    import atom
    MODULES = {
        "GoogleCalendarTwoWay" : { "type": "dataprovider" },
    }
except ImportError:
    MODULES = {
    }
    log.warn("Skipping GoogleCalendarTwoWay - GDATA is not available")

class GoogleConnection(object):
    def __init__(self):
        self.calService = gdata.calendar.service.CalendarService()
        self.calService.email = ""
        self.calService.password = ""
        self.selectedCalendar = GoogleCalendar('default', 'default')
        self.loggedIn = False

    def _connect(self):
        #Is there a automatic logout after a certain time?
        if self.loggedIn != True:
            self.calService.ProgrammaticLogin()
            self.loggedIn == True
        
    def SetUsername(self, username):
        if self.calService.email != username:
            self.calService.email = username
            self.loggedIn = False
    
    def GetUsername(self):
        return self.calService.email
    
    def SetPassword(self, password):
        self.calService.password = password
        
    def GetPassword(self):
        return self.calService.password
        
    def SetCalendar(self, googleCalendar):
        self.selectedCalendar = googleCalendar
        
    def GetCalendar(self):
        return self.selectedCalendar

    def AddEvent(self, googleEvent):
        self._connect()
        newEvent = self.calService.InsertEvent(googleEvent.GetGoogleFormat(), self.selectedCalendar.GetFeedLink())
        return GoogleEvent.FromGoogleFormat(newEvent)
        
    def DeleteEvent(self, googleEvent):
        self._connect()
        self.calService.DeleteEvent(googleEvent.GetEditLink())
    
    def Events(self):
        self._connect()
        calQuery = gdata.calendar.service.CalendarEventQuery(user = self.selectedCalendar.GetURI())
        eventFeed = self.calService.CalendarQuery(calQuery)
        for event in eventFeed.entry:   
            yield GoogleEvent.FromGoogleFormat(event)         

    def Calendars(self):
        self._connect()
        allCalendarsFeed = self.calService.GetCalendarListFeed().entry
        for calendarFeed in allCalendarsFeed:
            yield GoogleCalendar.FromGoogleFormat(calendarFeed)


class GoogleCalendar(object):
    def __init__(self, name, uri):
        self.uri = uri
        self.name = name
    
    def FromGoogleFormat(cls, calendar):
        uri = calendar.id.text.split('/')[-1]
        name = calendar.title.text
        return cls(name, uri)
    FromGoogleFormat = classmethod(FromGoogleFormat)
        
    def __eq__(self, other):
        if other is None:
            return False
        else:
            return self.GetURI() == other.GetURI()
        
    def GetURI(self):
        return self.uri
        
    def GetName(self):
        return self.name
    
    def GetFeedLink(self):
        return '/calendar/feeds/' + self.GetURI() + '/private/full'


def ConvertMadnessToDateTime(inputDate):
    dateStr = None
    dateDate = None
    dateDateTime = None
    dateTZInfo = None
    if isinstance(inputDate,str) or isinstance(inputDate, unicode):
        dateStr = inputDate
    if isinstance(inputDate, vobject.base.ContentLine):
        if isinstance(inputDate.value, unicode):
            dateStr = inputDate.value
        elif isinstance(inputDate.value, datetime.date):
            dateDate = inputDate.value
        elif isinstance(inputDate.value, datetime.datetime):
            dateDateTime = inputDate.value
            
    if dateStr is not None:
        if 'T' not in dateStr:
            dateDate =  dateutil.parser.parse(dateStr).date()
        else:
            dateDateTime = dateutil.parser.parse(dateStr)

    if dateDate is not None:
        return dateDate
        
    if dateDateTime is not None:
        if dateDateTime.tzinfo is not None:
            return dateDateTime
        elif dateTZInfo is not None:
            return dateDateTime.replace(tzinfo=dateTZInfo)
        else:
            log.warn('Waring, assuming datetime ('+dateDateTime.isoformat()+') is UTC')
            return dateDateTime.replace(tzinfo=tzutc())
                
    raise TypeError('Unable to convert to datetime')

         
def ParseGoogleRecur(recurString, args):
    vobjGoogle = vobject.readOne('BEGIN:VEVENT\r\n'+recurString+'\r\nEND:VEVENT\r\n')
    iCalString = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"
    if 'vtimezone' in vobjGoogle.contents:
        iCalString += vobjGoogle.vtimezone.serialize()
    iCalString += 'BEGIN:VEVENT\r\n'
    if 'dtend' in vobjGoogle.contents:
        iCalString += vobjGoogle.dtend.serialize()
    if 'dtstart' in vobjGoogle.contents:
        iCalString += vobjGoogle.dtstart.serialize()
    if 'rrule' in vobjGoogle.contents:
        iCalString += vobjGoogle.rrule.serialize()
    iCalString += 'END:VEVENT\r\nEND:VCALENDAR\r\n'

    vobjICal = vobject.readOne(iCalString)
    if 'dtstart' in vobjICal.vevent.contents:
        args['startTime'] = ConvertMadnessToDateTime(vobjICal.vevent.dtstart)
    if 'dtend' in vobjICal.vevent.contents:
        args['endTime'] = ConvertMadnessToDateTime(vobjICal.vevent.dtend)
    if 'rrule' in vobjICal.vevent.contents:
        args['recurrence'] = vobjICal.vevent.rrule.value
    if 'vtimezone' in vobjICal.contents:
        args['vtimezone'] = vobjICal.vtimezone

         
class GoogleEvent(object):
    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid', None)
        self.mTime = kwargs.get('mTime', None)
        self.title = kwargs.get('title', None)
        self.description = kwargs.get('description', None)
        self.location = kwargs.get('location', None)
        self.recurrence = kwargs.get('recurrence', None)
        self.startTime = kwargs.get('startTime', None)
        self.endTime = kwargs.get('endTime', None)
        self.vtimezone = kwargs.get('vtimezone',None)
        self.created = kwargs.get('created', None)
        self.visibility = kwargs.get('visibility', None)
        self.status = kwargs.get('status', None)
        self.editLink = kwargs.get('editLink', None)

    def FromICalFormat(cls, iCalString):
        args = dict()
        log.debug('Importing from iCal Event :\n'+iCalString)
        iCal = vobject.readOne(iCalString)
        iCalEvent = iCal.vevent
        if 'vtimezone' in iCal.contents:
            args['vtimezone'] = iCal.vtimezone
        if 'summary' in iCalEvent.contents:
            args['title'] = iCalEvent.summary.value
        if 'description' in iCalEvent.contents:
            args['description'] = iCalEvent.description.value
        if 'location' in iCalEvent.contents:
            args['location'] = iCalEvent.location.value
        if 'status' in iCalEvent.contents:
            args['status'] = iCalEvent.status.value
        if 'class' in iCalEvent.contents:
            args['visibility'] = iCalEvent.contents['class'][0].value
        if 'rrule' in iCalEvent.contents:
            args['recurrence'] = iCalEvent.rrule.value
        if 'dtstart' in iCalEvent.contents:
            args['startTime'] = ConvertMadnessToDateTime(iCalEvent.dtstart)
        if 'dtend' in iCalEvent.contents:
            args['endTime'] = ConvertMadnessToDateTime(iCalEvent.dtend)
        return cls(**args)
    FromICalFormat = classmethod(FromICalFormat)

    def FromGoogleFormat(cls, googleEvent):
        args = dict()
        log.debug('Importing from Google Event :\n'+str(googleEvent))
        if googleEvent.id.text is not None:
            args['uid'] = googleEvent.id.text.split('/')[-1] + "@google.com"
        if googleEvent.title.text is not None:    
            args['title'] = googleEvent.title.text
        if googleEvent.content.text is not None:
            args['description'] = googleEvent.content.text
        if googleEvent.where[0].value_string is not None:
            args['location'] = googleEvent.where[0].value_string
        if googleEvent.event_status.value is not None:
            args['status'] = googleEvent.event_status.value
        if googleEvent.visibility.value is not None:
            #Can't find out what default visibility is from gdata
            #See: http://code.google.com/p/gdata-issues/issues/detail?id=5
            if googleEvent.visibility.value != 'DEFAULT':
                args['visibility'] = googleEvent.visibility.value
        if googleEvent.published.text is not None:
            args['created'] =  ConvertMadnessToDateTime(googleEvent.published.text)
        if googleEvent.updated.text is not None:
            args['mTime'] =  ConvertMadnessToDateTime(googleEvent.updated.text)
        #iCalEvent.vevent.add('dtstamp').value = 
        if len(googleEvent.when) > 0:
            eventTimes = googleEvent.when[0]
            args['startTime'] = ConvertMadnessToDateTime(eventTimes.start_time)
            args['endTime'] = ConvertMadnessToDateTime(eventTimes.end_time)
        if googleEvent.recurrence is not None:
            ParseGoogleRecur(googleEvent.recurrence.text, args)
        args['editLink'] = googleEvent.GetEditLink().href
        return cls(**args)
    FromGoogleFormat = classmethod(FromGoogleFormat)
  
    def GetUID(self):
        return self.uid
        
    def GetMTime(self):
        #mtimes need to be naive and local
        #Shouldn't Conduit use non-naive mTimes?
        mTimeLocal = self.mTime.astimezone(tzlocal())
        mTimeLocalWithoutTZ = mTimeLocal.replace(tzinfo=None)
        return mTimeLocalWithoutTZ
        
    def GetEditLink(self):
        return self.editLink

    def GetGoogleFormat(self):
        googleEvent = gdata.calendar.CalendarEventEntry()        
        if self.title is not None:
            googleEvent.title = atom.Title(text=self.title)
        if self.description is not None:
            googleEvent.content = atom.Content(text=self.description)
        if self.location is not None:
            googleEvent.where.append(gdata.calendar.Where(value_string=self.location))
        if self.status is not None:
            status = gdata.calendar.EventStatus()
            status.value = self.status
            googleEvent.event_status = status
        if self.visibility is not None:
            vis = gdata.calendar.Visibility()
            vis.value = self.visibility
            googleEvent.visibility = vis
        if self.recurrence is not None:
            vobj = vobject.iCalendar().add('vevent')
            vobj.add('rrule').value = self.recurrence
            recurText = vobj.rrule.serialize()
            if self.startTime is not None:          
                vobj.add('dtstart').value = self.startTime
                recurText += vobj.dtstart.serialize()
            if self.endTime is not None:
                vobj.add('dtend').value = self.endTime
                recurText += vobj.dtend.serialize()
            if self.vtimezone is not None:
                vobj.add('vtimezone')
                vobj.vtimezone = self.vtimezone
                recurText += vobj.vtimezone.serialize()
            googleEvent.recurrence = gdata.calendar.Recurrence(text=recurText)
        else:
            eventTimes = gdata.calendar.When()
            eventTimes.start_time = self.startTime.isoformat()
            eventTimes.end_time = self.endTime.isoformat()
            googleEvent.when.append(eventTimes)
        log.debug("Created Google Format :\n"+str(googleEvent))
        return googleEvent

    def GetICalFormat(self):
        iCalEvent = vobject.iCalendar().add('vevent')
        if self.uid is not None:            
            iCalEvent.add('uid').value = self.uid
        if self.title is not None:    
            iCalEvent.add('summary').value = self.title
        if self.description is not None:
            iCalEvent.add('description').value = self.description
        if self.location is not None:
            iCalEvent.add('location').value = self.location
        if self.status is not None:
            iCalEvent.add('status').value = self.status
        if self.visibility is not None:
            iCalEvent.add('class').value = self.visibility
        if self.created is not None:
            iCalEvent.add('created').value = self.created.astimezone(tzutc())    
        if self.mTime is not None:
            iCalEvent.add('last-modified').value = self.mTime.astimezone(tzutc())
        #iCalEvent.vevent.add('dtstamp').value = 
        if self.recurrence is not None:
            iCalEvent.add('rrule').value = self.recurrence
        if self.startTime is not None:
            iCalEvent.add('dtstart').value = self.startTime
        if self.endTime is not None:
            iCalEvent.add('dtend').value = self.endTime
        returnStr = iCalEvent.serialize()
        log.debug("Created ICal Format :\n"+returnStr)
        return returnStr

    
class GoogleCalendarTwoWay(DataProvider.TwoWay):
    _name_ = "Google Calendar"
    _description_ = "Sync your Calendar"
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"
    
    def __init__(self):
        DataProvider.TwoWay.__init__(self)
        self.google = GoogleConnection()
        self.events = dict()
        self.need_configuration(True)
        self.set_configured(False)
        
    def _loadCalendars(self, widget, tree):
        import gtk, gtk.gdk
        dlg = tree.get_widget("GoogleCalendarConfigDialog")
        oldCursor = dlg.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        gtk.gdk.flush()
        
        sourceComboBox = tree.get_widget("sourceComboBox")
        store = sourceComboBox.get_model()
        store.clear()

        self.google.SetUsername(tree.get_widget("username").get_text())
        self.google.SetPassword(tree.get_widget("password").get_text())
        
        try:
            for calendar in self.google.Calendars():
                rowref = store.append( (calendar.GetName(), calendar) )
                if calendar == self.google.GetCalendar():
                    sourceComboBox.set_active_iter(rowref)
        except gdata.service.BadAuthentication:
            errorMsg = "Login Failed"
            errorDlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, message_format=errorMsg, buttons=gtk.BUTTONS_OK)
            errorDlg.run()
            errorDlg.destroy()
            dlg.window.set_cursor(oldCursor)
            return
            
        sourceComboBox.set_sensitive(True)
        tree.get_widget("calendarLbl").set_sensitive(True)
        tree.get_widget("okBtn").set_sensitive(True)
        dlg.window.set_cursor(oldCursor)
        
    def configure(self, window):
        import gtk
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "GoogleCalendarConfigDialog"
                        )

        tree.get_widget("username").set_text(self.google.GetUsername())
        tree.get_widget("password").set_text(self.google.GetPassword())
        
        sourceComboBox = tree.get_widget("sourceComboBox")       
        store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        sourceComboBox.set_model(store)

        cell = gtk.CellRendererText()
        sourceComboBox.pack_start(cell, True)
        sourceComboBox.add_attribute(cell, 'text', 0)
        sourceComboBox.set_active(0)

        selectedCalendar = self.google.GetCalendar()
        if selectedCalendar is not None:
            rowref = store.append( (selectedCalendar.GetName(), selectedCalendar) )
            sourceComboBox.set_active_iter(rowref)

        dlg = tree.get_widget("GoogleCalendarConfigDialog")
        
        signalConnections = { "on_loadCalendarsBtn_clicked" : (self._loadCalendars, tree) }
        tree.signal_autoconnect( signalConnections )
        
        response = Utils.run_dialog(dlg, window)
        if response == True:
            self.google.SetCalendar( store.get_value(sourceComboBox.get_active_iter(), 1) )
            self.set_configured(True)
        dlg.destroy()  
        
    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.events.clear()
        for event in self.google.Events():
            self.events[event.GetUID()] = event
        
    def finish(self):
        self.events.clear()
        
    def get_all(self):
        return self.events.keys()
        
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self) 
        return len(self.events)

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)       
        event = self.events[LUID]
        conduitEvent = Event.Event(LUID)
        conduitEvent.set_from_ical_string(event.GetICalFormat())
        conduitEvent.set_mtime(event.GetMTime())
        conduitEvent.set_UID(event.GetUID())
        return conduitEvent          
                   
    def _createEvent(self, conduitEvent):
        googleEvent = GoogleEvent.FromICalFormat( conduitEvent.get_ical_string() )
        newEvent = self.google.AddEvent( googleEvent )
        return Rid(uid=newEvent.GetUID(), mtime=None, hash=None)
        
    def _deleteEvent(self, LUID):
        self.google.DeleteEvent( self.events[LUID] )
        
    def _updateEvent(self, LUID, conduitEvent):
        self._deleteEvent(LUID)
        rid = self._createEvent(conduitEvent)
        return rid

    def delete(self, LUID):
        self._deleteEvent(LUID)
        
    def put(self, obj, overwrite, LUID=None):
        #Following taken from EvolutionModule
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)
        if LUID != None:
            existing = self.events.get(LUID, None)
            if existing != None:
                if overwrite == True:
                    rid = self._updateEvent(LUID, obj)
                    return rid
                else:
                    comp = obj.compare(existing)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, existing, obj)
                    else:
                        # overwrite and return new ID
                        rid = self._updateEvent(LUID, obj)
                        return rid

        # if we get here then it is new...
        log.info("Creating new object")
        rid = self._createEvent(obj)
        return rid
        
    def get_configuration(self):
        config = dict()
        selectedCalendar = self.google.GetCalendar()
        if selectedCalendar is not None:
            config['selectedCalendarName'] = selectedCalendar.GetName()
            config['selectedCalendarURI'] = selectedCalendar.GetURI()
        if self.google is not None:
            config['username'] = self.google.GetUsername()
            config['password'] = self.google.GetPassword()
        config['isConfigured'] = self.isConfigured
        return config
            
    def set_configuration(self, config):
        if 'username' in config:
            self.google.SetUsername(config['username'])
        if 'password' in config:
            self.google.SetPassword(config['password'])
        if ('selectedCalendarName' in config) and ('selectedCalendarURI' in config):
            self.google.SetCalendar( GoogleCalendar(config['selectedCalendarName'], config['selectedCalendarURI']) )
        self.set_configured( config['isConfigured'] )
         
    def get_UID(self):
        return self.google.GetUsername()
		
