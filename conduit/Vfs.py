import logging
log = logging.getLogger("Vfs")

try:
    import gnomevfs
except ImportError:
    from gnome import gnomevfs

MONITOR_EVENT_CREATED =             gnomevfs.MONITOR_EVENT_CREATED
MONITOR_EVENT_CHANGED =             gnomevfs.MONITOR_EVENT_CHANGED
MONITOR_EVENT_DELETED =             gnomevfs.MONITOR_EVENT_DELETED
MONITOR_EVENT_METADATA_CHANGED =    gnomevfs.MONITOR_EVENT_METADATA_CHANGED
MONITOR_EVENT_STARTEXECUTING =      gnomevfs.MONITOR_EVENT_STARTEXECUTING
MONITOR_EVENT_STOPEXECUTING =       gnomevfs.MONITOR_EVENT_STOPEXECUTING
MONITOR_FILE =                      gnomevfs.MONITOR_FILE
MONITOR_DIRECTORY =                 gnomevfs.MONITOR_DIRECTORY

class VolumeMonitor(gnomevfs.VolumeMonitor):
    pass

def monitor_add(folder, type, monitor_cb):
    try:
        return gnomevfs.monitor_add (folder, type, monitor_cb)
    except gnomevfs.NotSupportedError:
        # silently fail if we are looking at a folder that doesn't support directory monitoring
        return None

def monitor_cancel(monitor_id):
    gnomevfs.monitor_cancel(monitor_id)

def get_filesystem_type(uri):
    """
    @returns: The filesystem that uri is stored on or None if it cannot
    be determined
    """
    scheme = gnomevfs.get_uri_scheme(uri)
    if scheme == "file":
        try:
            path = gnomevfs.get_local_path_from_uri(uri)
            volume = VolumeMonitor().get_volume_for_path(path)
            return  volume.get_filesystem_type()
        except RuntimeError:
            log.warn("Could not get local path from URI")
            return None
        except AttributeError:
            log.warn("Could not determine volume for path")
            return None
    return None






