import dbus, dbus.glib

# we only operate on directories
SUPPORTED_FORMAT = 'x-directory/normal'

#dbus interfaces
APPLICATION_DBUS_IFACE='org.conduit.Application'
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
SYNCSET_DBUS_IFACE="org.conduit.SyncSet"

# supported dps
FLICKR_TWOWAY="FlickrTwoWay"
FOLDER_TWOWAY="FolderTwoWay"

def get_conduit_app ():
    bus = dbus.SessionBus()

    try:
        remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
        return dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)
    except dbus.exceptions.DBusException:
        return None

if __name__ == "__main__":
    app = get_conduit_app()
    
    if not app:
        print "Check Conduit Running"
        exit()

    # check if they needed providers are available
    dps = app.GetAllDataProviders()

    if not FOLDER_TWOWAY in dps or not FLICKR_TWOWAY in dps:
        print "Could not find folder/flickr"
        exit()

    bus = dbus.SessionBus()

    # create dataproviders
    folder_twoway_path = app.GetDataProvider(FOLDER_TWOWAY)
    sink_path = app.GetDataProvider(FLICKR_TWOWAY)

    # now create conduit
    conduit_path = app.BuildConduit (folder_twoway_path, sink_path)
    conduit_obj = bus.get_object(CONDUIT_DBUS_IFACE, conduit_path)
    
    # syncset
    ss = bus.get_object(SYNCSET_DBUS_IFACE, "/syncset/gui")
    ss.AddConduit(conduit_obj, dbus_interface=SYNCSET_DBUS_IFACE)
    
    

