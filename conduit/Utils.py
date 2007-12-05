"""
Utility Functions

Part of this code copied from from Listen (c) 2006 Mehdi Abaakouk
(http://listengnome.free.fr/)

Copyright: John Stowers, 2006
License: GPLv2
"""
import sys
import os
import os.path
import socket
import datetime
import time
import re
import os
import signal
import popen2
try:
    import gnomevfs
except ImportError:
    from gnome import gnomevfs # for maemo

import logging
log = logging.getLogger("Utils")

def get_proportional_resize(desiredW, desiredH, currentW, currentH):
    """
    Returns proportionally resized co-ordinates for an image
    """
    #Account for 'dont care about this axis sizing'
    if desiredH == None: desiredH = currentH
    if desiredW == None: desiredW = currentW

    #Calculate the axis of most change
    dw = abs(currentW - desiredW)
    dh = abs(currentH - desiredH)

    if dh > dw:
        newHeight = float(desiredH)
        percentage = newHeight / currentH
        newWidth = currentW * percentage
    else:
        newWidth = float(desiredW)
        percentage = newWidth / currentW
        newHeight = currentH * percentage

    return int(newWidth), int(newHeight)    
    
def program_installed(app):
    """
    Check if the given app is installed.
    """
    path = os.environ['PATH'] 
    paths = path.split(os.pathsep)
    for dir in paths:
        if os.path.isdir(dir):
            if os.path.isfile(os.path.join(dir,app)):
                return True
    return False

#
# URI Manipulation functions
#
def uri_make_canonical(uri):
    """
    Standardizes the format of the uri
    @param uri:an absolute or relative stringified uri. It might have scheme.
    """
    return gnomevfs.make_uri_canonical(uri)
    
def uri_escape(uri):
    """
    Escapes a uri, replacing only special characters that would not be found in 
    paths or host names.
    (so '/', '&', '=', ':' and '@' will not be escaped by this function)
    """
    #FIXME: This function lies, it escapes @
    #return gnomevfs.escape_host_and_path_string(uri)
    import urllib
    return urllib.quote(uri,safe='/&=:@')
    
def uri_unescape(uri):
    """
    Replace "%xx" escapes by their single-character equivalent.
    """
    import urllib
    return urllib.unquote(uri)
    
def uri_get_protocol(uri):
    """
    Returns the protocol (file, smb, etc) for a URI
    """
    if uri.rfind("://")==-1:
        return ""
    protocol = uri[:uri.index("://")+3]
    return protocol.lower()

def uri_get_filename(path):
    """
    Method to return the filename of a file. Could use GnomeVFS for this
    is it wasnt so slow
    """
    return path.split(os.sep)[-1]

#
# Temporary file functions
#
def new_tempfile(contents, contentsAreText=True):
    """
    Returns a new File onject, which has been created in the 
    system temporary directory, and that has been filled with
    contents
    
    The file is closed when it is returned
    
    @param contents: The data to write into the file
    @param contentsAreText: Indicates to the OS if the file is text (as opposed
    to a binary type file
    @param contentsAreText: C{bool}
    @returns: a L{conduit.datatypes.File}
    """
    import conduit.datatypes.File as File
    return File.TempFile(contents)

def new_tempdir():
    """
    Creates a new temporary directory
    """
    import tempfile
    return tempfile.mkdtemp("conduit")

def unique_list(seq):
    """
    The fastes way to unique-ify a list while retaining its order, from
    http://www.peterbe.com/plog/uniqifiers-benchmark
    """
    def _f10(listy):
        seen = set()
        for x in listy:
            if x in seen:
                continue
            seen.add(x)
            yield x
    return list(_f10(seq))

def random_string(length=5):
    """
    returns a random string of length
    """
    import random
    s = ""
    for i in range(1,length):
        s += str(random.randint(0,10))
    return s

def dataprovider_add_dir_to_path(dataproviderfile, directory=""):
    """
    Adds directory to the python search path.

    From within a dataprovider (FooModule.py) 
    call with Utils.dataprovider_add_dir_to_path(__file__, some_dir):
    """
    path = os.path.join(dataproviderfile, "..", directory)
    path = os.path.abspath(path)
    log.debug("Adding %s to python path" % path)
    sys.path.insert(0,path)

def dataprovider_glade_get_widget(dataproviderfile, gladefilename, widget):
    """
    Gets a single gtk widget from a glad file
    """
    import gtk.glade
    path = os.path.join(dataproviderfile, "..", gladefilename)
    path = os.path.abspath(path)
    return gtk.glade.XML(path, widget)

def run_dialog(dialog, window=None):
    """
    Runs a given dialog, and makes it transient for
    the given window if any
    @param dialog: dialog 
    @param window: gtk window
    @returns: True if the user clicked OK to exit the dialog
    """
    import gtk

    if window:
        dialog.set_transient_for(window)

    return dialog.run() == gtk.RESPONSE_OK

def md5_string(string):
    """
    Returns the md5 of the supplied string in readable hexdigest string format
    """
    import md5
    return md5.new(string).hexdigest()

def uuid_string():
    """
    Returns a uuid string
    """
    try:
        import uuid
        return uuid.uuid4().hex
    except ImportError:
        import time, random, md5, socket
        t = long( time.time() * 1000 )
        r = long( random.random()*100000000000000000L )
        try:
            a = socket.gethostbyname( socket.gethostname() )
        except:
            a = random.random()*100000000000000000L
        data = str(t)+' '+str(r)+' '+str(a)
        data = md5.md5(data).hexdigest()
        return data

def dbus_service_available(bus,interface):
    """
    Checks if a dbus service is available on the given bus
    """
    try: 
        import dbus
    except: 
        return False
    obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
    dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
    avail = dbus_iface.ListNames()
    return interface in avail

def get_user_string():
    """
    Makes a user and machine dependant string in the form
    username@hostname
    """
    hostname = socket.gethostname()
    username = os.environ.get("USER","")
    return "%s@%s" % (username, hostname)

def open_URI(uri):
    """
    Opens a gnomevfs or xdg compatible uri.
    FIXME: Use xdg-open?
    """
    if uri == None:
        log.warn("Cannot open non-existant URI")

    APP = "gnome-open"
    os.spawnlp(os.P_NOWAIT, APP, APP, uri)

def datetime_from_timestamp(t):
    """
    Makes a datetime object from a unix timestamp.

    Note: For the sake of consistancy always drop the
    fractional (microsecond) part of the timestamp
    """
    if type(t) not in [long, int, float]:
        raise Exception("Timestamp must be a number")

    if t < 0:
        raise Exception("Timestamps before 1970 are not valid")

    return datetime.datetime.fromtimestamp(long(t))

def datetime_get_timestamp(d):
    """
    Returns the unix timestamp for a datetime

    Note: For the sake of consistancy always drop the
    fractional (microsecond) part of the timestamp
    """
    import time, datetime
    if type(d) != datetime.datetime:
        raise Exception("Must supply a datetime")

    f = time.mktime(d.timetuple())
    if f < 0:
        raise Exception("Timestamps before 1970 are not valid")

    return long(f)

def encode_conversion_args(args):
    """
    encodes an args dictionary to a url string in the form
    param=value&param2=val2
    """
    import urllib
    return urllib.urlencode(args)

def decode_conversion_args(argString):
    """
    FIXME: dont import cgi for just one function. Also it doesnt
    even handle lists
    """
    import cgi
    args = {}
    for key,val in cgi.parse_qsl(argString):
        args[key] = val
    return args

#
# Memstats
#
class Memstats(object):
    """
    Memory analysis functions taken from
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/286222
    """

    _proc_status = '/proc/%d/status' % os.getpid()
    _scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
              'KB': 1024.0, 'MB': 1024.0*1024.0}
              
    def __init__(self):
        self.prev = [0.0,0.0,0.0]

    def _VmB(self, VmKey):
         # get pseudo file  /proc/<pid>/status
        try:
            t = open(self._proc_status)
            v = t.read()
            t.close()
        except Exception, err:
            return 0.0  # non-Linux?
         # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
        i = v.index(VmKey)
        v = v[i:].split(None, 3)  # whitespace
        if len(v) < 3:
            return 0.0  # invalid format?
         # convert Vm value to bytes
        return float(v[1]) * self._scale[v[2]]
        
    def calculate(self):
        VmSize = self._VmB('VmSize:') - self.prev[0]
        VmRSS = self._VmB('VmRSS:') - self.prev [1]
        VmStack = self._VmB('VmStk:') - self.prev [2]
        log.debug("Memory Stats: VM=%sMB RSS=%sMB STACK=%sMB" %(
                                    VmSize  / self._scale["MB"],
                                    VmRSS   / self._scale["MB"],
                                    VmStack / self._scale["MB"],
                                    ))
        return VmSize,VmRSS,VmStack 

#
# Scanner ThreadManager
#
class ScannerThreadManager(object):
    """
    Manages many FolderScanner threads. This involves joining and cancelling
    said threads, and respecting a maximum num of concurrent threads limit
    """
    def __init__(self, maxConcurrentThreads=2):
        self.maxConcurrentThreads = maxConcurrentThreads
        self.scanThreads = {}
        self.pendingScanThreadsURIs = []

    def make_thread(self, folderURI, includeHidden, progressCb, completedCb, *args):
        """
        Makes a thread for scanning folderURI. The thread callsback the model
        at regular intervals with the supplied args
        """
        running = len(self.scanThreads) - len(self.pendingScanThreadsURIs)

        if folderURI not in self.scanThreads:
            thread = FolderScanner(folderURI, includeHidden)
            thread.connect("scan-progress",progressCb, *args)
            thread.connect("scan-completed",completedCb, *args)
            thread.connect("scan-completed", self._register_thread_completed, folderURI)
            self.scanThreads[folderURI] = thread
            if running < self.maxConcurrentThreads:
                log.debug("Starting thread %s" % folderURI)
                self.scanThreads[folderURI].start()
            else:
                self.pendingScanThreadsURIs.append(folderURI)
            return thread
        else:
            return self.scanThreads[folderURI]

    def _register_thread_completed(self, sender, folderURI):
        """
        Decrements the count of concurrent threads and starts any 
        pending threads if there is space
        """
        #delete the old thread
        del(self.scanThreads[folderURI])
        running = len(self.scanThreads) - len(self.pendingScanThreadsURIs)

        log.debug("Thread %s completed. %s running, %s pending" % (folderURI, running, len(self.pendingScanThreadsURIs)))

        if running < self.maxConcurrentThreads:
            try:
                uri = self.pendingScanThreadsURIs.pop()
                log.debug("Starting pending thread %s" % uri)
                self.scanThreads[uri].start()
            except IndexError: pass

    def join_all_threads(self):
        """
        Joins all threads (blocks)

        Unfortunately we join all the threads do it in a loop to account
        for join() a non started thread failing. To compensate I time.sleep()
        to not smoke CPU
        """
        joinedThreads = 0
        while(joinedThreads < len(self.scanThreads)):
            for thread in self.scanThreads.values():
                try:
                    thread.join()
                    joinedThreads += 1
                except AssertionError: 
                    #deal with not started threads
                    time.sleep(1)

    def cancel_all_threads(self):
        """
        Cancels all threads ASAP. My block for a small period of time
        because we use our own cancel method
        """
        for thread in self.scanThreads.values():
            if thread.isAlive():
                log.debug("Cancelling thread %s" % thread)
                thread.cancel()
            thread.join() #May block

#
# FOLDER SCANNER
#
import threading
import gobject
import time

CONFIG_FILE_NAME = ".conduit.conf"

class FolderScanner(threading.Thread, gobject.GObject):
    """
    Recursively scans a given folder URI, returning the number of
    contained files.
    """
    __gsignals__ =  { 
                    "scan-progress": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_INT]),
                    "scan-completed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    def __init__(self, baseURI, includeHidden):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.baseURI = str(baseURI)
        self.includeHidden = includeHidden

        self.dirs = [self.baseURI]
        self.cancelled = False
        self.URIs = []
        self.setName("FolderScanner Thread: %s" % self.baseURI)

    def run(self):
        """
        Recursively adds all files in dirs within the given list.
        
        Code adapted from Listen (c) 2006 Mehdi Abaakouk
        (http://listengnome.free.fr/)
        """
        delta = 0
        
        startTime = time.time()
        t = 1
        last_estimated = estimated = 0 
        while len(self.dirs)>0:
            if self.cancelled:
                return
            dir = self.dirs.pop(0)
            try:hdir = gnomevfs.DirectoryHandle(dir)
            except: 
                log.warn("Folder %s Not found" % dir)
                continue
            try: fileinfo = hdir.next()
            except StopIteration: continue;
            while fileinfo:
                filename = uri_escape(fileinfo.name)
                if filename in [".","..",CONFIG_FILE_NAME]: 
                        pass
                else:
                    if fileinfo.type == gnomevfs.FILE_TYPE_DIRECTORY:
                        #Include hidden directories
                        if filename[0] != "." or self.includeHidden:
                            self.dirs.append(dir+"/"+filename)
                            t += 1
                    elif fileinfo.type == gnomevfs.FILE_TYPE_REGULAR:
                        try:
                            uri = uri_make_canonical(dir+"/"+filename)
                            #Include hidden files
                            if filename[0] != "." or self.includeHidden:
                                self.URIs.append(uri)
                        except UnicodeDecodeError:
                            raise "UnicodeDecodeError",uri
                    else:
                        log.debug("Unsupported file type: %s (%s)" % (filename, fileinfo.type))
                try: fileinfo = hdir.next()
                except StopIteration: break;
            #Calculate the estimated complete percentags
            estimated = 1.0-float(len(self.dirs))/float(t)
            estimated *= 100
            #Enly emit progress signals every 10% (+/- 1%) change to save CPU
            if delta+10 - estimated <= 1:
                log.debug("Folder scan %s%% complete" % estimated)
                self.emit("scan-progress", len(self.URIs))
                delta += 10
            last_estimated = estimated

        i = 0
        total = len(self.URIs)
        endTime = time.time()
        log.debug("%s files loaded in %s seconds" % (total, (endTime - startTime)))
        self.emit("scan-completed")

    def cancel(self):
        """
        Cancels the thread as soon as possible.
        """
        self.cancelled = True

    def get_uris(self):
        return self.URIs

class CommandLineConverter:
    def __init__(self):
        self.percentage_match = re.compile('.*')

    def _kill(self, process):
        log.debug("Killing process")
        os.kill(process.pid, signal.SIGKILL)

    def build_command(self, command, **params):
        self.command = command
        
    def calculate_percentage(self, val):
        return float(val)

    def check_cancelled(self):
        return False

    def convert( self, input_filename, output_filename, callback=None,save_output=False):
        command = self.command % (input_filename, output_filename)
        log.debug("Executing %s" % command)

        output = ""
        process = popen2.Popen4(command)
        stdout = process.fromchild
        s = stdout.read(80)
        if save_output:
            output += s
        while s:
            if callback:
                for i in self.percentage_match.finditer(s):
                    val = self.calculate_percentage(i.group(1).strip())
                    callback(val)
            if save_output:
                output += s
            if self.check_cancelled():
                self._kill(process)
            s = stdout.read(80)

        ok = process.wait() == 0
        if save_output:
            return ok, output
        else:
            return ok
            

