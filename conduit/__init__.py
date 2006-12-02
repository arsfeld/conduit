"""
Introduction
============
    Conduit is a synchronization solution for GNOME which allows the user to 
    take their emails, files, bookmarks, and any other type of personal 
    information and synchronize that data with another computer, an online 
    service, or even another electronic device.

Conduit manages the synchronization and conversion of data into other formats. 
For example, conduit allows you to;

 1. Synchronize your tomboy notes to a file on a remote computer
 2. Synchronize your emails to your mobile phone
 3. Synchronize your bookmarks to delicious, gmail, or even your own webserver
 4. and many more... 

Any combination you can imagine, Conduit will take care of the conversion 
and synchronization. 

Copyright: John Stowers, 2006
License: GPLv2
"""

import logging
import os
import gobject
gobject.threads_init()

APPNAME="Conduit"
APPVERSION="0.3.0"

# Check the profile directory to prevent crashes when saving settings, etc
USER_DIR = os.path.join(os.environ['HOME'],".conduit")
if not os.path.exists(USER_DIR):
    os.mkdir(USER_DIR)

# If the CONDUIT_LOGLEVEL evironment variable is set then this 
#overrides the settings below
DEFAULT_LOG_LEVEL = "DEBUG"
LOG_DICT = {"INFO" : logging.INFO,
            "DEBUG" : logging.DEBUG,
            "WARNING" : logging.WARNING,
            "ERROR" : logging.ERROR,
            "CRITICAL" : logging.CRITICAL
            }
    
try:
    LOG_LEVEL = os.environ['CONDUIT_LOGLEVEL']
    level=LOG_DICT[LOG_LEVEL]
except KeyError:
    LOG_LEVEL = DEFAULT_LOG_LEVEL
    level = LOG_DICT[LOG_LEVEL]

logging.basicConfig(level=level,
                    format='[%(levelname)7s] %(message)s')
#                    filename=os.path.join(USER_DIR, "conduit.log"),
#                    filemode='w')

#Shorthand log functions to save typing
def log(message):
    logging.info(message)
def logd(message):
    logging.debug(message)
def logw(message):
    logging.warn(message)

#Memory analysis functions taken from
#http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/286222
_proc_status = '/proc/%d/status' % os.getpid()
_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

def _VmB(VmKey):
    global _proc_status, _scale
     # get pseudo file  /proc/<pid>/status
    try:
        t = open(_proc_status)
        v = t.read()
        t.close()
    except:
        return 0.0  # non-Linux?
     # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = v.index(VmKey)
    v = v[i:].split(None, 3)  # whitespace
    if len(v) < 3:
        return 0.0  # invalid format?
     # convert Vm value to bytes
    return float(v[1]) * _scale[v[2]]

def memstats(prev=(0.0,0.0,0.0)):
    global _scale
    VmSize = _VmB('VmSize:') - prev[0]
    VmRSS = _VmB('VmRSS:') - prev [1]
    VmStack = _VmB('VmStk:') - prev [2]

    logd("Memory Stats: VM=%sMB RSS=%sMB STACK=%sMB" %(
                                    VmSize  / _scale["MB"],
                                    VmRSS   / _scale["MB"],
                                    VmStack / _scale["MB"],
                                    ))
    return VmSize,VmRSS,VmStack 

#Globale settings object to be used by all
import Settings
settings = Settings.Settings()

