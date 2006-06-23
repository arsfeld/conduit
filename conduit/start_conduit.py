import MainWindow
import sys
from os.path import *

# Allow to use uninstalled
def _check(path):
    return exists(path) and isdir(path) and isfile(path+"/ChangeLog")

name = join(dirname(__file__), '.')
if _check(name):
	print 'Running uninstalled deskbar, modifying PYTHONPATH'
	sys.path.insert(0, abspath(name))
else:
	sys.path.insert(0, abspath("@PYTHONDIR@"))
	print "Running installed deskbar, using [@PYTHONDIR@:$PYTHONPATH]"




test = MainWindow.MainWindow("Conduit Test Application")
test.__main__()
 
