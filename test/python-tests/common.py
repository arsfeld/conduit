import sys
import os

# make sure we have conduit folder in path!
my_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(my_path, '..', '..'))
sys.path.insert(0, base_path)

# import main conduit module
import conduit

# set up expected paths & variables 
conduit.IS_INSTALLED =          False
conduit.SHARED_DATA_DIR =       os.path.join(base_path,"data")
conduit.GLADE_FILE =            os.path.join(base_path,"data","conduit.glade")
conduit.SHARED_MODULE_DIR =     os.path.join(base_path,"conduit")
conduit.EXTRA_LIB_DIR =         os.path.join(base_path,"contrib")

def ok(message, code):
    if type(code) == int:
        if code == -1:
            print "[FAIL] %s" % message
            sys.exit()
        else:
            print "[PASS] %s" % message
            return code
    elif type(code) == bool:
        if code == True:
            print "[PASS] %s" % message
        else:
            print "[FAIL] %s" % message
            sys.exit()
