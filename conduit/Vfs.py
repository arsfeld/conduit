try:
    import gnomevfs
except ImportError:
    from gnome import gnomevfs

# to add: STARTEXECUTING, STOPEXECUTING, METADATA_CHANGED  
MONITOR_EVENT_CREATED = gnomevfs.MONITOR_EVENT_CREATED
MONITOR_EVENT_CHANGED = gnomevfs.MONITOR_EVENT_CHANGED
MONITOR_EVENT_DELETED = gnomevfs.MONITOR_EVENT_DELETED

MONITOR_DIRECTORY = gnomevfs.MONITOR_DIRECTORY

def monitor_add(folder, type, monitor_cb):
    try:
        return gnomevfs.monitor_add (folder, type, monitor_cb)
    except gnomevfs.NotSupportedError:
        # silently fail if we are looking at a folder that doesn't support directory monitoring
        return None

def monitor_cancel(monitor_id):
    gnomevfs.monitor_cancel(monitor_id)

class VolumeMonitor(gnomevfs.VolumeMonitor):
    pass




