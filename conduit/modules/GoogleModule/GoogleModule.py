import gobject
import datetime
import dateutil.parser
import vobject
from dateutil.tz import tzutc, tzlocal
import logging
log = logging.getLogger("modules.Google")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.Image as Image
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Event as Event
import conduit.datatypes.Photo as Photo
import conduit.datatypes.Video as Video

from gettext import gettext as _

import re

#Distributors, if you ship python gdata >= 1.0.10 then remove this line
#and the appropriate directories
Utils.dataprovider_add_dir_to_path(__file__)
import atom
import gdata
import gdata.service
import gdata.photos
import gdata.photos.service    
import gdata.calendar
import gdata.calendar.service

# time format
FORMAT_STRING = "%Y-%m-%dT%H:%M:%S"

MODULES = {
    "GoogleCalendarTwoWay" : { "type": "dataprovider" },
    "PicasaTwoWay" :         { "type": "dataprovider" },
    "YouTubeSource" :        { "type": "dataprovider" },       
}


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
    _name_ = _("Google Calendar")
    _description_ = _("Sync your Google Calendar")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"
    
    def __init__(self):
        DataProvider.TwoWay.__init__(self)
        self.google = GoogleConnection()
        self.events = dict()
        
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
                        "calendar-config.glade",
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
        dlg.destroy()  
        
    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.events.clear()
        for event in self.google.Events():
            self.events[event.GetUID()] = event
        
    def finish(self, aborted, error, conflict):
        self.events.clear()
        
    def get_all(self):
        return self.events.keys()
        
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self) 
        return len(self.events)

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)       
        event = self.events[LUID]
        conduitEvent = Event.Event()
        conduitEvent.set_from_ical_string(event.GetICalFormat())
        conduitEvent.set_open_URI(LUID)
        conduitEvent.set_mtime(event.GetMTime())
        conduitEvent.set_UID(event.GetUID())
        return conduitEvent
        
    def is_configured (self, isSource, isTwoWay):
        if len(self.google.GetUsername()) < 1:
            return False
        if len(self.google.GetPassword()) < 1:
            return False
        return True   
                   
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
        return config
            
    def set_configuration(self, config):
        if 'username' in config:
            self.google.SetUsername(config['username'])
        if 'password' in config:
            self.google.SetPassword(config['password'])
        if ('selectedCalendarName' in config) and ('selectedCalendarURI' in config):
            self.google.SetCalendar( GoogleCalendar(config['selectedCalendarName'], config['selectedCalendarURI']) )
         
    def get_UID(self):
        return self.google.GetUsername()

class PicasaTwoWay(Image.ImageTwoWay):

    _name_ = _("Picasa")
    _description_ = _("Sync your Google Picasa photos")
    _icon_ = "picasa"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        
        self.username = ""
        self.password = ""
        self.album = ""
        self.imageSize = "None"

        self.pws = gdata.photos.service.PhotosService()
        self.galbum = None
        self.gphoto_dict = None

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo.GetMediaURL()

    def _get_photo_info (self, id):
        if self.gphoto_dict.has_key(id):
            return self.gphoto_dict[id]
        else:
            return None
            
    def _get_photo_formats (self):
        return ("image/jpeg", )
        
    def refresh(self):
        Image.ImageTwoWay.refresh(self)
        self._login()
        self._get_album()
        self._get_photos()

    def get_all (self):
        return self.gphoto_dict.keys()
        
    def get (self, LUID):
        Image.ImageTwoWay.get (self, LUID)

        gphoto = self.gphoto_dict[LUID]
        url = gphoto.GetMediaURL()

        tags = (tag.title.text for tag in self.pws.GetFeed(gphoto.GetTagsUri()).entry)

        f = Photo.Photo (URI=url)
        f.force_new_mtime(self._get_photo_timestamp(gphoto))
        f.set_open_URI(url)
        f.set_UID(LUID)
        f.set_tags(tags)

        return f

    def delete(self, LUID):
        if not self.gphoto_dict.has_key(LUID):
            log.warn("Photo does not exit")
            return

        self.pws.Delete(self.gphoto_dict[LUID])
        del self.gphoto_dict[LUID]

    def _upload_photo (self, uploadInfo):
        try:
            gphoto = self.pws.InsertPhotoSimple (self.galbum, uploadInfo.name, '', uploadInfo.url)

            for tag in uploadInfo.tags:
                self.pws.InsertTag(gphoto, str(tag))

            return Rid(uid=gphoto.gphoto_id.text)
        except Exception, e:
            raise Exceptions.SyncronizeError("Picasa Upload Error.")

    def _login(self):
        self.pws.ClientLogin(self.username, self.password)

    def _get_album(self):
        configured_album = None

        albums = self.pws.GetUserFeed().entry

        for album in albums:
            if album.title.text != self.album:
                continue

            log.debug("Found album %s" % self.album)
            configured_album = album
            break

        if not configured_album:
            log.debug("Creating new album %s." % self.album)
            configured_album = self.pws.InsertAlbum (self.album, '')

        self.galbum = configured_album

    def _get_photos(self):
        self.gphoto_dict = {}

        for photo in self.pws.GetFeed(self.galbum.GetPhotosUri()).entry:
            self.gphoto_dict[photo.gphoto_id.text] = photo

    def _get_photo_timestamp(self, gphoto):
        from datetime import datetime
        timestamp = gphoto.updated.text[0:-5]
        try:
            return datetime.strptime(timestamp, FORMAT_STRING)
        except AttributeError:
            import time
            return datetime(*(time.strptime(timestamp, FORMAT_STRING)[0:6]))

    def configure(self, window):
        """
        Configures the PicasaTwoWay
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "picasa-config.glade", 
                        "PicasaTwoWayConfigDialog")
                        
        #get a whole bunch of widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        album = widget.get_widget("album")                
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)
        album.set_text (self.album)

        resizecombobox = widget.get_widget("combobox1")
        self._resize_combobox_build(resizecombobox, self.imageSize)
        
        dlg = widget.get_widget("PicasaTwoWayConfigDialog")
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.username = username.get_text()
            self.password = password.get_text()
            self.album = album.get_text()
            self.imageSize = self._resize_combobox_get_active(resizecombobox)
        dlg.destroy()    
        
    def get_configuration(self):
        return {
            "imageSize" : self.imageSize,
            "username" : self.username,
            "password" : self.password,
            "album" : self.album
            }
            
    def is_configured (self, isSource, isTwoWay):
        if len(self.username) < 1:
            return False
        if len(self.password) < 1:
            return False
        if len(self.album) < 1:
            return False
        return True

    def get_UID(self):
        return self.username
            
class YouTubeSource(DataProvider.DataSource):
    _name_ = _("YouTube")
    _description_ = _("Sync data from YouTube")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _out_type_ = "file/video"
    _icon_ = "youtube"

    _const_users_feed = "http://gdata.youtube.com/feeds/users"
    _const_std_feeds = "http://gdata.youtube.com/feeds/standardfeeds"
    _video_name_re = re.compile(r', "t": "([^"]+)"')

    #Config args
    max = 0
    #filter type {0 = mostviewed, 1 = toprated, 2 = user}
    filter_type = 0
    #filter user type {0 = upload, 1 = favorites}
    user_filter_type = 0
    username = ""


    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.entries = None

    def initialize(self):
        return True

    def configure(self, window):
        tree = Utils.dataprovider_glade_get_widget (
                __file__,
                "youtube-config.glade",
                "YouTubeSourceConfigDialog") 

        dlg = tree.get_widget ("YouTubeSourceConfigDialog")
        mostviewedRb = tree.get_widget("mostviewed")
        topratedRb = tree.get_widget("toprated")
        byuserRb = tree.get_widget("byuser")
        user_frame = tree.get_widget("frame")
        uploadedbyRb = tree.get_widget("uploadedby")
        favoritesofRb = tree.get_widget("favoritesof")
        user = tree.get_widget("user")
        maxdownloads = tree.get_widget("maxdownloads")

        byuserRb.connect("toggled", self._filter_user_toggled_cb, user_frame)

        if self.filter_type == 0:
            mostviewedRb.set_active(True)
        elif self.filter_type == 1:
            topratedRb.set_active(True)
        else:
            byuserRb.set_active(True)
            user_frame.set_sensitive(True)
            if self.user_filter_type == 0:
                uploadedbyRb.set_active(True)
            else:
                favoritesofRb.set_active(True)
            user.set_text(self.username)

        log.debug("Max")
        log.debug(self.max)
        maxdownloads.set_value(self.max)

        response = Utils.run_dialog(dlg, window)
        if response == True:
            if mostviewedRb.get_active():
                self.filter_type = 0
            elif topratedRb.get_active():
                self.filter_type = 1
            else:
                self.filter_type = 2
                if uploadedbyRb.get_active():
                    self.user_filter_type = 0
                else:
                    self.user_filter_type = 1
                self.username = user.get_text()
            self.max = int(maxdownloads.get_value())

        dlg.destroy()

    def refresh(self):
        DataProvider.DataSource.refresh(self)

        self.entries = {}
        try:
            feedUrl = ""
            if self.filter_type == 0:
                videos = self._most_viewed ()
            elif self.filter_type == 1:
                videos = self._top_rated ()
            else:
                if self.usr_filter_type == 0:
                    videos = self._videos_upload_by (self.username)
                else:
                    videos = self._favorite_videos (self.username)

            for video in videos:
                self.entries[video.title.text] = self._get_flv_video_url (video.link[1].href)
        except Exception, err:
            log.debug("Error getting/parsing feed (%s)" % err)
            raise Exceptions.RefreshError

    def get_all(self):
        return self.entries.keys()

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        url = self.entries[LUID]
        log.debug("Title: '%s', Url: '%s'"%(LUID, url))

        f = Video.Video(URI=url)
        f.set_open_URI(url)
        f.set_UID(LUID)
        f.force_new_filename (str(LUID) + ".flv")

        return f

    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.files = None

    def get_configuration(self):
        return {
            "filter_type" : self.filter_type,
            "user_filter_type" : self.user_filter_type,
            "username" : self.username,
            "max" : self.max
        }


    def get_UID(self):
        return Utils.get_user_string()

    #ui callbacks
    def _filter_user_toggled_cb (self, toggle, frame):
        frame.set_sensitive(toggle.get_active())


    """
    Code based on youtube client from : Philippe Normand (phil at base-art dot net)
    """
    def _format_url (self, url):
        if self.max > 0:
            url = ("%s?max-results=%d" % (url, self.max))

        return url

    def _request(self, feed, *params):
        service = gdata.service.GDataService(server="gdata.youtube.com")
        return service.Get(feed % params)

    def _top_rated(self):
        url = self._format_url ("%s/top_rated" % self._const_std_feeds)
        return self._request(url).entry

    def _most_viewed(self):
        url = self._format_url ("%s/most_viewed" % self._const_std_feeds)
        return self._request(url).entry

    def _videos_upload_by(self, username):
        url = self._format_url ("%s/%s/uploads" % (self._const_users_feed, username))
        return self._request(url).entry

    def _favorite_videos(self, username):
        url = self._format_url ("%s/%s/favorites" % (self._const_users_feed, username))
        return self._request(url).entry


    # Generic extract step
    def _get_flv_video_url (self, url):
        import urllib2
        flv_url = ''
        doc = urllib2.urlopen(url)
        data = doc.read()

        # extract video name
        match = self._video_name_re.search(data)
        if match is not None:
            video_name = match.group(1)

            # extract video id
            url_splited = url.split("watch?v=")
            video_id = url_splited[1]

            flv_url = "http://www.youtube.com/get_video?video_id=%s&t=%s"
            flv_url = flv_url % (video_id, video_name)

        return flv_url

