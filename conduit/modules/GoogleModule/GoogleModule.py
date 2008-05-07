import re
import gobject
import datetime
import dateutil.parser
import vobject
import operator
import time
from dateutil.tz import tzutc, tzlocal
from gettext import gettext as _
import logging
log = logging.getLogger("modules.Google")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.Image as Image
import conduit.utils as Utils
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event
import conduit.datatypes.Photo as Photo
import conduit.datatypes.Video as Video
import conduit.datatypes.File as File

#Distributors, if you ship python gdata >= 1.0.10 then remove this line
#and the appropriate directories
Utils.dataprovider_add_dir_to_path(__file__)
try:
    import atom.service
    import gdata.service
    import gdata.photos.service    
    import gdata.calendar.service
    import gdata.contacts.service
    import gdata.docs.service

    MODULES = {
        "GoogleCalendarTwoWay" : { "type": "dataprovider" },
        "PicasaTwoWay" :         { "type": "dataprovider" },
        "YouTubeSource" :        { "type": "dataprovider" },    
        "ContactsTwoWay" :       { "type": "dataprovider" },
        "DocumentsSink" :        { "type": "dataprovider" },
    }
    log.info("Module Information: %s" % Utils.get_module_information(gdata, None))
except (ImportError, AttributeError):
    MODULES = {}
    log.info("Google support disabled")

# time format
FORMAT_STRING = "%Y-%m-%dT%H:%M:%S"

class GoogleBase(object):
    def __init__(self):
        self.username = ""
        self.password = ""
        self.loggedIn = False
        
    def _do_login(self):
        raise NotImplementedError

    def _login(self):
        if not self.loggedIn:
            try:
                self._do_login()
                self.loggedIn = True
            except gdata.service.BadAuthentication:
                log.info("Error logging in: Incorrect username or password")
            except Exception, e:
                log.info("Error logging in: %s" % e)
       
    def _set_username(self, username):
        if self.username != username:
            self.username = username
            self.loggedIn = False
    
    def _set_password(self, password):
        if self.password != password:
            self.password = password
            self.loggedIn = False

    def set_configuration(self, config):
        self._set_username(config.get("username",""))
        self._set_password(config.get("password",""))

    def get_configuration(self):
        return {
            "username": self.username,
            "password": self.password
            }

    def is_configured (self, isSource, isTwoWay):
        if len(self.username) < 1:
            return False
        if len(self.password) < 1:
            return False
        return True

    def get_UID(self):
        return self.username

class GoogleCalendar(object):
    def __init__(self, name, uri):
        self.uri = uri
        self.name = name

    @classmethod    
    def from_google_format(cls, calendar):
        uri = calendar.id.text.split('/')[-1]
        name = calendar.title.text
        return cls(name, uri)
        
    def __eq__(self, other):
        if other is None:
            return False
        else:
            return self.get_uri() == other.get_uri()
        
    def get_uri(self):
        return self.uri
        
    def get_name(self):
        return self.name
    
    def get_feed_link(self):
        return '/calendar/feeds/' + self.get_uri() + '/private/full'

def convert_madness_to_datetime(inputDate):
    log.debug('Attempting to parse the following: %s'%inputDate)
    logging.debug('Attempting to parse the following: %s'%inputDate)
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
            logging.warn("returning: %s",dateDateTime)
            ts = dateDateTime.timetuple()
            dateDateTime = dateDateTime.fromtimestamp(time.mktime(ts))
            return dateDateTime
        elif dateTZInfo is not None:
            return dateDateTime.replace(tzinfo=dateTZInfo)
        else:
            log.warn('Waring, assuming datetime ('+dateDateTime.isoformat()+') is UTC')
            return dateDateTime.replace(tzinfo=tzutc())
                
    
    raise TypeError('Unable to convert to datetime')

def parse_google_recur(recurString, args):
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
        args['startTime'] = convert_madness_to_datetime(vobjICal.vevent.dtstart)
    if 'dtend' in vobjICal.vevent.contents:
        args['endTime'] = convert_madness_to_datetime(vobjICal.vevent.dtend)
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

    @classmethod
    def from_ical_format(cls, iCalString):
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
            args['startTime'] = convert_madness_to_datetime(iCalEvent.dtstart)
        if 'dtend' in iCalEvent.contents:
            args['endTime'] = convert_madness_to_datetime(iCalEvent.dtend)
        return cls(**args)

    @classmethod
    def from_google_format(cls, googleEvent):
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
            args['created'] =  convert_madness_to_datetime(googleEvent.published.text)
        if googleEvent.updated.text is not None:
            args['mTime'] =  convert_madness_to_datetime(googleEvent.updated.text)
        #iCalEvent.vevent.add('dtstamp').value = 
        if len(googleEvent.when) > 0:
            eventTimes = googleEvent.when[0]
            args['startTime'] = convert_madness_to_datetime(eventTimes.start_time)
            args['endTime'] = convert_madness_to_datetime(eventTimes.end_time)
        if googleEvent.recurrence is not None:
            parse_google_recur(googleEvent.recurrence.text, args)
        args['editLink'] = googleEvent.GetEditLink().href
        return cls(**args)
  
    def get_uid(self):
        return self.uid
        
    def get_mtime(self):
        #mtimes need to be naive and local
        #Shouldn't Conduit use non-naive mTimes?
        try:
            mTimeLocal = self.mTime.astimezone(tzlocal())
        except ValueError:
            mTimeLocal = self.mTime
        mTimeLocalWithoutTZ = mTimeLocal.replace(tzinfo=None)
        return mTimeLocalWithoutTZ
        
    def get_edit_link(self):
        return self.editLink

    def get_google_format(self):
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

    def get_ical_format(self):
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
            try:
                iCalEvent.add('created').value = self.created.astimezone(tzutc())
            except ValueError: pass
        if self.mTime is not None:
            try:
                iCalEvent.add('last-modified').value = self.mTime.astimezone(tzutc())
            except ValueError: pass
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
    
class GoogleCalendarTwoWay(GoogleBase, DataProvider.TwoWay):

    _name_ = _("Google Calendar")
    _description_ = _("Sync your Google Calendar")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "appointment-new"
    
    def __init__(self):
        GoogleBase.__init__(self)
        DataProvider.TwoWay.__init__(self)
        self.calService = gdata.calendar.service.CalendarService()
        self.selectedCalendar = None
        self.events = {}

    def _do_login(self):
        self.calService.ClientLogin(self.username, self.password)

    def _get_all_events(self):
        self._login()
        calQuery = gdata.calendar.service.CalendarEventQuery(user = self.selectedCalendar.get_uri())
        eventFeed = self.calService.CalendarQuery(calQuery)
        for event in eventFeed.entry:   
            yield GoogleEvent.from_google_format(event)

    def _get_all_calendars(self):
        self._login()
        allCalendarsFeed = self.calService.GetCalendarListFeed().entry
        for calendarFeed in allCalendarsFeed:
            yield GoogleCalendar.from_google_format(calendarFeed)

    def _load_calendars(self, widget, tree):
        import gtk, gtk.gdk
        dlg = tree.get_widget("GoogleCalendarConfigDialog")
        oldCursor = dlg.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        gtk.gdk.flush()
        
        sourceComboBox = tree.get_widget("sourceComboBox")
        store = sourceComboBox.get_model()
        store.clear()

        self._set_username(tree.get_widget("username").get_text())
        self._set_password(tree.get_widget("password").get_text())
        
        try:
            for calendar in self._get_all_calendars():
                rowref = store.append( (calendar.get_name(), calendar) )
                if calendar == self.selectedCalendar:
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

        tree.get_widget("username").set_text(self.username)
        tree.get_widget("password").set_text(self.password)
        
        sourceComboBox = tree.get_widget("sourceComboBox")       
        store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        sourceComboBox.set_model(store)

        cell = gtk.CellRendererText()
        sourceComboBox.pack_start(cell, True)
        sourceComboBox.add_attribute(cell, 'text', 0)
        sourceComboBox.set_active(0)

        if self.selectedCalendar is not None:
            rowref = store.append( (self.selectedCalendar.get_name(), self.selectedCalendar) )
            sourceComboBox.set_active_iter(rowref)
        signalConnections = { "on_loadCalendarsBtn_clicked" : (self._load_calendars, tree) }
        tree.signal_autoconnect( signalConnections )

        dlg = tree.get_widget("GoogleCalendarConfigDialog")        
        response = Utils.run_dialog(dlg, window)
        if response == True:
            self.selectedCalendar = store.get_value(sourceComboBox.get_active_iter(),1)
        dlg.destroy()  
        
    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.events = {}
        for event in self._get_all_events():
            self.events[event.get_uid()] = event
        
    def finish(self, aborted, error, conflict):
        self.events = {}
        
    def get_all(self):
        return self.events.keys()
        
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self) 
        return len(self.events)

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)       
        event = self.events[LUID]
        conduitEvent = Event.Event()
        conduitEvent.set_from_ical_string(event.get_ical_format())
        conduitEvent.set_open_URI(LUID)
        conduitEvent.set_mtime(event.get_mtime())
        conduitEvent.set_UID(event.get_uid())
        return conduitEvent          
                   
    def _create_event(self, conduitEvent):
        googleEvent = GoogleEvent.from_ical_format( conduitEvent.get_ical_string() )
        newEvent = self.calService.InsertEvent(
                                        googleEvent.get_google_format(),
                                        self.selectedCalendar.get_feed_link())
        newEvent = GoogleEvent.from_google_format(newEvent)
        return Rid(uid=newEvent.get_uid(), mtime=None, hash=None)
        
    def _delete_event(self, LUID):
        googleEvent = self.events[LUID]
        self.calService.DeleteEvent(googleEvent.get_edit_link())
        
    def _update_event(self, LUID, conduitEvent):
        self._delete_event(LUID)
        rid = self._create_event(conduitEvent)
        return rid

    def delete(self, LUID):
        self._delete_event(LUID)
        
    def put(self, obj, overwrite, LUID=None):
        #Following taken from EvolutionModule
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)
        if LUID != None:
            existing = self.events.get(LUID, None)
            if existing != None:
                if overwrite == True:
                    rid = self._update_event(LUID, obj)
                    return rid
                else:
                    comp = obj.compare(existing)
                    # only update if newer
                    if comp != conduit.datatypes.COMPARISON_NEWER:
                        raise Exceptions.SynchronizeConflictError(comp, existing, obj)
                    else:
                        # overwrite and return new ID
                        rid = self._update_event(LUID, obj)
                        return rid

        # if we get here then it is new...
        log.info("Creating new object")
        rid = self._create_event(obj)
        return rid
        
    def get_configuration(self):
        conf = GoogleBase.get_configuration(self)
        if self.selectedCalendar != None:
            conf.update({
                "selectedCalendarName"  :   self.selectedCalendar.get_name(),
                "selectedCalendarURI"   :   self.selectedCalendar.get_uri()})
        return conf
            
    def set_configuration(self, config):
        GoogleBase.set_configuration(self, config)
        if "selectedCalendarName" in config:
            if "selectedCalendarURI" in config:
                self.selectedCalendar = GoogleCalendar(
                                            config['selectedCalendarName'],
                                            config['selectedCalendarURI']
                                            )

    def is_configured (self, isSource, isTwoWay):
        if not GoogleBase.is_configured(self, isSource, isTwoWay):
            return False
        if self.selectedCalendar == None:
            return False
        return True

class PicasaTwoWay(GoogleBase, Image.ImageTwoWay):

    _name_ = _("Picasa")
    _description_ = _("Sync your Google Picasa photos")
    _icon_ = "picasa"

    def __init__(self, *args):
        GoogleBase.__init__(self)
        Image.ImageTwoWay.__init__(self)
        self.albumName = ""
        self.imageSize = "None"
        self.pws = gdata.photos.service.PhotosService()
        self.galbum = None
        self.gphoto_dict = {}

    def _get_raw_photo_url(self, photoInfo):
        return photoInfo.GetMediaURL()

    def _get_photo_info (self, id):
        if self.gphoto_dict.has_key(id):
            return self.gphoto_dict[id]
        else:
            return None
            
    def _get_photo_formats (self):
        return ("image/jpeg",)
        
    def _upload_photo (self, uploadInfo):
        try:
            gphoto = self.pws.InsertPhotoSimple(
                                self.galbum,
                                uploadInfo.name,
                                uploadInfo.caption,
                                uploadInfo.url)
            for tag in uploadInfo.tags:
                self.pws.InsertTag(gphoto, str(tag))
            return Rid(uid=gphoto.gphoto_id.text)
        except Exception, e:
            raise Exceptions.SyncronizeError("Picasa Upload Error.")

    def _do_login(self):
        self.pws.ClientLogin(self.username, self.password)

    def _get_album(self):
        for name,album in self._get_albums():
            if name == self.albumName:
                log.debug("Found album %s" % self.albumName)
                self.galbum = album
                return

        log.debug("Creating new album %s." % self.albumName)
        self.galbum = self._create_album(self.albumName)

    def _get_albums(self):
        albums = []
        for album in self.pws.GetUserFeed().entry:
            albums.append(
                    (album.title.text,  #album name
                    album))             #album
        return albums
        
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

    def _create_album(self, album_name):            
        self.pws.InsertAlbum(album_name, '', access='private')

    def refresh(self):
        Image.ImageTwoWay.refresh(self)
        self._login()
        if not self.loggedIn:
            raise Exceptions.RefreshError("Could not log in")
        self._get_album()

    def get_all (self):
        Image.ImageTwoWay.get_all(self)
        self._get_photos()
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
        f.set_caption(gphoto.summary.text)
        return f

    def delete(self, LUID):
        if not self.gphoto_dict.has_key(LUID):
            log.warn("Photo does not exit")
            return

        self.pws.Delete(self.gphoto_dict[LUID])
        del self.gphoto_dict[LUID]

    def configure(self, window):
        """
        Configures the PicasaTwoWay
        """
        import gobject
        import gtk
        def on_login_finish(*args):
            if self.loggedIn:
                build_album_model()
            Utils.dialog_reset_cursor(dlg)
                
        def on_response(sender, responseID):
            if responseID == gtk.RESPONSE_OK:
                self._set_username(username.get_text())
                self._set_password(password.get_text())
                self.albumName = album_combo.get_active_text()
                self.imageSize = self._resize_combobox_get_active(resizecombobox)

        def login_click(button, window, usernameEntry, passwordEntry):
            self._set_username(usernameEntry.get_text())
            self._set_password(passwordEntry.get_text())
            Utils.dialog_set_busy_cursor(dlg)
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                                            self,
                                            on_login_finish,
                                            self._login)        

        def username_password_changed(sender, username, password, login_button):
            login_button.set_sensitive(
                            len(username.get_text()) > 0 and len(password.get_text()) > 0)

        def build_album_model():
            album_store.clear()
            album_count = 0
            album_iter = None
            for name, album in self._get_albums():       
                iter = album_store.append((name,))
                if name == self.albumName:
                    album_iter = iter
                album_count += 1

            if album_iter:
                album_combo.set_active_iter(album_iter)
            elif self.albumName:
                album_combo.child.set_text(self.albumName)
            elif album_count:
                album_combo.set_active(0)
        
        #get widget and dialog 
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "picasa-config.glade", 
                        "PicasaTwoWayConfigDialog")

        #get a whole bunch of widgets
        username = tree.get_widget('username')
        password = tree.get_widget('password')
        album_combo = tree.get_widget('album_combobox')
        login_button = tree.get_widget("login_button")
        dlg = tree.get_widget("PicasaTwoWayConfigDialog")        

        resizecombobox = tree.get_widget("resize_combobox")
        self._resize_combobox_build(resizecombobox, self.imageSize)

        #connect to signals
        login_button.connect('clicked', login_click, window, username, password)
        username.connect('changed', username_password_changed, username, password, login_button)
        password.connect('changed', username_password_changed, username, password, login_button)
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)

        #setup album combo
        album_store = gtk.ListStore(gobject.TYPE_STRING)
        album_combo.set_model (album_store)
        cell = gtk.CellRendererText()
        album_combo.pack_start(cell, True)
        album_combo.set_text_column(0)
        
        #disable album lookup if no username entered
        enabled = len(self.username) > 0
        login_button.set_sensitive(enabled)

        # Now run the dialog 
        Utils.run_dialog_non_blocking(dlg, on_response, window)
        
    def get_configuration(self):
        conf = GoogleBase.get_configuration(self)
        conf.update({
            "imageSize" :   self.imageSize,
            "album"     :   self.albumName})
        return conf
        
    def set_configuration(self, config):
        GoogleBase.set_configuration(self, config)
        self.imageSize = config.get("imageSize","None")
        self.albumName = config.get("album","")

    def is_configured (self, isSource, isTwoWay):
        if not GoogleBase.is_configured(self, isSource, isTwoWay):
            return False
        if len(self.albumName) < 1:
            return False
        return True


class ContactsTwoWay(GoogleBase,  DataProvider.TwoWay):
    """
    Contacts GData provider
    """
    _name_ = _("Google Contacts")
    _description_ = _("Sync your Gmail contacts")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        GoogleBase.__init__(self)
        DataProvider.TwoWay.__init__(self)
        self.service = gdata.contacts.service.ContactsService()
        
    def _google_contact_from_conduit_contact(self, contact, gc=None):
        """
        Fills the apropriate fields in the google gdata contact type based on
        those in the conduit contact type
        """
        name = contact.get_name()
        emails = contact.get_emails()
        #Google contacts must feature at least a name and an email address
        if not (name and emails):
            return None

        #can also edit existing contacts
        if not gc:
            gc = gdata.contacts.ContactEntry()        
        gc.title = atom.Title(text=name)

        #Create all emails, make first one primary, if the contact doesnt
        #already have a primary email address
        primary = 'false'
        existing = []
        for ex in gc.email:
            if ex.primary and ex.primary == 'true':
                primary = 'true'
                existing.append(ex)      
        
        for email in emails:
            if email not in existing:
                log.debug("Adding new email address %s %s" % (email, existing))
                gc.email.append(gdata.contacts.Email(
                                            address=email, 
                                            primary=primary))#,rel=gdata.contacts.REL_WORK))
                primary = 'false'
        #notes = contact.get_notes()
        #if notes: gc.content = atom.Content(text=notes)
        
        return gc

        
    def _conduit_contact_from_google_contact(self, gc):
        """
        Extracts available and interesting fields from the google contact
        and stored them in the conduit contact type
        """
        c = Contact.Contact(formattedName=str(gc.title.text))
        
        emails = [str(e.address) for e in gc.email]
        c.set_emails(*emails)
        
        #ee_names = map(operator.attrgetter('tag'),gc.extension_elements)
        #if len(gc.extension_elements) >0:
        #    for e in [e for e in ee_names if e == 'phoneNumber']:
        #        c.vcard.add('tel')
        #        c.vcard.tel.value = gc.extension_elements[ee_names.index('phoneNumber')].text
        #        c.vcard.tel.type_param = gc.extension_elements[ee_names.index('phoneNumber')].attributes['rel'].split('#')[1]
        #    for e in [e for e in ee_names if e == 'postalAddress']:
        #        c.vcard.add('adr')
        #        c.vcard.adr.value = vobject.vcard.Address(gc.extension_elements[ee_names.index('postalAddress')].text)
        #        c.vcard.adr.type_param = gc.extension_elements[ee_names.index('postalAddress')].attributes['rel'].split('#')[1]
        
        return c

    def _do_login(self):
        self.service.ClientLogin(self.username, self.password)
        
    def _create_contact(self, contact):
        gc = self._google_contact_from_conduit_contact(contact)
        if not gc:
            log.info("Could not create google contact from conduit contact")
            return None

        try:            
            entry = self.service.CreateContact(gc)
        except gdata.service.RequestError, e:
            #If the response dict reson is 'Conflict' then we are trying to
            #store a contact with the same email as one which already exists
            if e.message.get("reason","") == "Conflict":
                log.warn("FIXME: FIND THE OLD CONTACT BY EMAIL, GET IT, AND RAISE A CONFLICT EXCEPTION")
                raise Exceptions.SynchronizeConflictError("FIXME", "FIXME", "FIXME")
        except Exception, e:
            log.warn("Error creating contact: %s" % e)
            return None

        if entry:
            log.debug("Created contact: %s" % entry.id.text)
            return entry.id.text
        else:
            log.debug("Create contact error")
            return None

    def _update_contact(self, LUID, contact):
        #get the gdata contact from google
        try:
            oldgc = self.service.Get(LUID, converter=gdata.contacts.ContactEntryFromString)
        except gdata.service.RequestError:
            return None
            
        #update the contact
        gc = self._google_contact_from_conduit_contact(contact, oldgc)
        self.service.UpdateContact(oldgc.GetEditLink().href, gc)
        
        #fixme, we should really just return the RID here, but its safer
        #to use the same code path as get, because I am not sure if/how google
        #changes the mtime
        return LUID
    
    def _get_contact(self, LUID):
        if not LUID:
            return None

        #get the gdata contact from google
        try:
            gc = self.service.Get(LUID, converter=gdata.contacts.ContactEntryFromString)
        except gdata.service.RequestError:
            return None
            
        c = self._conduit_contact_from_google_contact(gc)
        c.set_UID(LUID)
        c.set_mtime(convert_madness_to_datetime(gc.updated.text))
        return c

    def _get_all_contacts(self):
        feed = self.service.GetContactsFeed()
        if not feed.entry:
            return []
        return [str(contact.id.text) for contact in feed.entry]
        
    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self._login()
        if not self.loggedIn:
            raise Exceptions.RefreshError("Could not log in")

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        self._login()
        return self._get_all_contacts()

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        self._login()
        c = self._get_contact(LUID)
        if c == None:
            log.warn("Error getting/parsing gdata contact")
        return c
        
    def put(self, data, overwrite, LUID=None):
        #http://www.conduit-project.org/wiki/WritingADataProvider/GeneralPutInstructions
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        if overwrite and LUID:
            LUID = self._update_contact(LUID, data)
        else:
            oldData = self._get_contact(LUID)
            if LUID and oldData:
                comp = data.compare(oldData)
                #Possibility 1: If LUID != None (i.e this is a modification/update of a 
                #previous sync, and we are newer, the go ahead an put the data
                if LUID != None and comp == conduit.datatypes.COMPARISON_NEWER:
                    LUID = self._update_contact(LUID, data)
                #Possibility 3: We are the same, so return either rid
                elif comp == conduit.datatypes.COMPARISON_EQUAL:
                    return oldData.get_rid()
                #Possibility 2, 4: All that remains are conflicts
                else:
                    raise Exceptions.SynchronizeConflictError(comp, data, oldData)
            else:
                #Possibility 5:
                LUID = self._create_contact(data)
                
        #now return the rid
        if not LUID:
            raise Exceptions.SyncronizeError("Google contacts upload error.")
        else:
            return self._get_contact(LUID).get_rid()


    def delete(self, LUID):
        DataProvider.TwoWay.delete(self, LUID)
        self._login()
        #get the gdata contact from google
        try:
            gc = self.service.Get(LUID, converter=gdata.contacts.ContactEntryFromString)
            self.service.DeleteContact(gc.GetEditLink().href)
        except gdata.service.RequestError, e:
            log.warn("Error deleting: %s" % e)        

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)

    def configure(self, window):
        """
        Configures the PicasaTwoWay
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "contacts-config.glade", 
                        "GoogleContactsConfigDialog")
                        
        #get a whole bunch of widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)
        
        dlg = widget.get_widget("GoogleContactsConfigDialog")
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self._set_username(username.get_text())
            self._set_password(password.get_text())
        dlg.destroy()    

class DocumentsSink(GoogleBase,  DataProvider.DataSink):
    """
    Contacts GData provider
    
    See: http://code.google.com/p/gdatacopier/source/browse/trunk/python/gdatacopier.py
    """
    _name_ = _("Google Documents")
    _description_ = _("Sync your Google Documents")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _out_type_ = "contact"
    _icon_ = "applications-office"
    
    SUPPORTED_DOCUMENTS = ('DOC','ODT','SWX','TXT','RTF','HTM','HTML')
    SUPPORTED_SHEETS = ('ODS','XLS','CSV','TSV')
    SUPPORTED_PRESENTATIONS = ('PPT','PPS')
    
    TYPE_DOCUMENT = 'document'
    TYPE_SPREADSHEET = 'spreadsheet'
    TYPE_PRESENTATION = 'presentation'

    def __init__(self, *args):
        GoogleBase.__init__(self)
        DataProvider.DataSink.__init__(self)
        self.service = gdata.docs.service.DocsService()
        
    def _do_login(self):
        self.service.ClientLogin(self.username, self.password)
        
    def _upload_document(self, f):
        name,ext = f.get_filename_and_extension()
        ext = ext[1:].upper()

        ms = gdata.MediaSource(
                    file_path=f.get_local_uri(),
                    content_type=gdata.docs.service.SUPPORTED_FILETYPES[ext])

        #upload using the appropriate service
        if ext in self.SUPPORTED_DOCUMENTS:
            entry = self.service.UploadDocument(ms,name)
        elif ext in self.SUPPORTED_SHEETS:
            entry = self.service.UploadSpreadsheet(ms,name)
        elif ext in self.SUPPORTED_PRESENTATIONS:
            entry = self.service.UploadPresentation(ms,name)
        else:
            log.info("Unknown document format")
            return None

        return entry.id.text
        
    def _get_all_documents(self):
        feed = self.service.GetDocumentListFeed()
        if not feed.entry:
            return []
        return [str(doc.id.text) for doc in feed.entry]
        
    def _get_document(self, LUID):
        if not LUID:
            return None

        #get the gdata contact from google
        try:
            gd = self.service.GetDocumentListEntry(LUID)
        except gdata.service.RequestError:
            return None

        return gd
        
    # Parses the document id out of the alternate link url, the atom feed
    # doesn't actually provide the document id      
    def _get_document_id(self, LUID):
        from urlparse import *
        parsed_url = urlparse(LUID)
        url_params = parsed_url[4]
        document_id = url_params.split('=')[1]
        return document_id
        
    def _download_doc(self, LUID):
        docid = self._get_document_id(LUID)
    
        #self.service.debug = True
        #https://docs.google.com/MiscCommands?command=saveasdoc&exportformat=%s&docID=%s
        resp = atom.service.HttpRequest(
                                service=self.service,
                                operation='GET',
                                data=None,
                                uri='/MiscCommands',
                                extra_headers={'Authorization':self.service._GetAuthToken()},
                                url_params={'command':'saveasdoc','exportformat':'doc','docID':docid},
                                escape_params=True,
                                content_type='application/atom+xml')

        path = "/home/john/Desktop/%s.doc" % docid
        file_handle = open(path, 'wb')
        file_handle.write(resp.read())
        file_handle.close()
        
        return path
        
    def refresh(self):
        DataProvider.DataSink.refresh(self)
        self._login()
        if not self.loggedIn:
            raise Exceptions.RefreshError("Could not log in")

#    def put(self, doc, overwrite, LUID=None):            
#        #Check if we have already uploaded the document
#        if LUID != None:
#            info = self._get_photo_info(LUID)
#            #check if a photo exists at that UID
#            if info != None:
#                if overwrite == True:
#                    #replace the photo
#                    return self._replace_photo(LUID, uploadInfo)
#                else:
#                    #Only upload the photo if it is newer than the Remote one
#                    url = self._get_raw_photo_url(info)
#                    remoteFile = File.File(url)
#
#                    #this is a limited test for equality type comparison
#                    comp = photo.compare(remoteFile,True)
#                    log.debug("Compared %s with %s to check if they are the same (size). Result = %s" % 
#                            (photo.get_filename(),remoteFile.get_filename(),comp))
#                    if comp != conduit.datatypes.COMPARISON_EQUAL:
#                        raise Exceptions.SynchronizeConflictError(comp, photo, remoteFile)
#                    else:
#                        return conduit.datatypes.Rid(uid=LUID)
#
#        log.debug("Uploading Photo URI = %s, Mimetype = %s, Original Name = %s" % (photoURI, mimeType, originalName))
#
#        #upload the file
#        return self._upload_photo (uploadInfo)

    def delete(self, LUID):
        DataProvider.DataSink.delete(self, LUID)
        self._login()
        #get the gdata contact from google
        #try:
        #    gc = self.service.Get(LUID, converter=gdata.contacts.ContactEntryFromString)
        #    self.service.DeleteContact(gc.GetEditLink().href)
        #except gdata.service.RequestError, e:
        #    log.warn("Error deleting: %s" % e)        

    def configure(self, window):
        """
        Configures the PicasaTwoWay
        """
        widget = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "contacts-config.glade", 
                        "GoogleContactsConfigDialog")
                        
        #get a whole bunch of widgets
        username = widget.get_widget("username")
        password = widget.get_widget("password")
        
        #preload the widgets        
        username.set_text(self.username)
        password.set_text(self.password)
        
        dlg = widget.get_widget("GoogleContactsConfigDialog")
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self._set_username(username.get_text())
            self._set_password(password.get_text())
        dlg.destroy()   

class YouTubeSource(DataProvider.DataSource):
    """
    Downloads YouTube videos using the gdata API.
    Based on youtube client from : Philippe Normand (phil at base-art dot net)
    http://base-art.net/Articles/87/
    """
    _name_ = _("YouTube")
    _description_ = _("Sync data from YouTube")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _out_type_ = "file/video"
    _icon_ = "youtube"

    USERS_FEED = "http://gdata.youtube.com/feeds/users"
    STD_FEEDS = "http://gdata.youtube.com/feeds/standardfeeds"
    VIDEO_NAME_RE = re.compile(r', "t": "([^"]+)"')
    
    #From: http://code.google.com/apis/youtube/dashboard/
    UPLOAD_CLIENT_ID="ytapi-ConduitProject-Conduit-e14hdhdm-0"
    UPLOAD_DEVELOPER_KEY="AI39si6wJ3VA_UWZCWeuA-wmJEpEhGbE3ZxCOZq89JJFy5CpSkFOq8gdZluNvBAM6DW8m7AhliSYPLyfEPJx6XphBq3vOBHuzQ"
    UPLOAD_URL="http://uploads.gdata.youtube.com/feeds/api/users/%(username)s/uploads"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.entries = None
        self.username = ""
        self.max_downloads = 0
        #filter type {0 = mostviewed, 1 = toprated, 2 = user}
        self.filter_type = 0
        #filter user type {0 = upload, 1 = favorites}
        self.user_filter_type = 0

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
        maxdownloads.set_value(self.max_downloads)

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
            self.max_downloads = int(maxdownloads.get_value())

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
                if self.user_filter_type == 0:
                    videos = self._videos_upload_by (self.username)
                else:
                    videos = self._favorite_videos (self.username)

            for video in videos:
                self.entries[video.title.text] = self._get_flv_video_url (video.link[0].href)
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
            "filter_type"       :   self.filter_type,
            "user_filter_type"  :   self.user_filter_type,
            "username"          :   self.username,
            "max_downloads"     :   self.max_downloads
        }

    def get_UID(self):
        return Utils.get_user_string()

    def _filter_user_toggled_cb (self, toggle, frame):
        frame.set_sensitive(toggle.get_active())

    def _format_url (self, url):
        if self.max_downloads > 0:
            url = ("%s?max-results=%d" % (url, self.max_downloads))
        return url

    def _request(self, feed, *params):
        service = gdata.service.GDataService(server="gdata.youtube.com")
        return service.Get(feed % params)

    def _top_rated(self):
        url = self._format_url ("%s/top_rated" % YouTubeSource.STD_FEEDS)
        return self._request(url).entry

    def _most_viewed(self):
        url = self._format_url ("%s/most_viewed" % YouTubeSource.STD_FEEDS)
        return self._request(url).entry

    def _videos_upload_by(self, username):
        url = self._format_url ("%s/%s/uploads" % (YouTubeSource.USERS_FEED, username))
        return self._request(url).entry

    def _favorite_videos(self, username):
        url = self._format_url ("%s/%s/favorites" % (YouTubeSource.USERS_FEED, username))
        return self._request(url).entry

    # Generic extract step
    def _get_flv_video_url (self, url):
        import urllib2
        flv_url = ''
        doc = urllib2.urlopen(url)
        data = doc.read()

        # extract video name
        match = YouTubeSource.VIDEO_NAME_RE.search(data)
        if match is not None:
            video_name = match.group(1)

            # extract video id
            url_splited = url.split("watch?v=")
            video_id = url_splited[1]

            flv_url = "http://www.youtube.com/get_video?video_id=%s&t=%s"
            flv_url = flv_url % (video_id, video_name)
    
        log.debug ("FLV URL %s" % flv_url)

        return flv_url

