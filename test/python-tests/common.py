import sys
import os
import glob

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

def ok(message, code, die=True):
    if type(code) == int:
        if code == -1:
            print "[FAIL] %s" % message
            if die:
                sys.exit()
            return False
        else:
            print "[PASS] %s" % message
            return True
    elif type(code) == bool:
        if code == False:
            print "[FAIL] %s" % message
            if die:
                sys.exit()
            return False
        else:
            print "[PASS] %s" % message
            return True

#returns list of files that match the glob in the data dir
def get_files_from_data_dir(glob_str):
    files = []
    for i in glob.glob(os.path.join(os.path.dirname(__file__),"data",glob_str)):
        files.append(os.path.abspath(i))
    return files

#returns the contents of the file called name in the data dir
def read_data_file(name):
    f = open(name,'r')
    txt = f.read()
    f.close()
    return txt

