import sys
import os

# make sure we have conduit folder in path!
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, script_path)

# import main conduit module
import conduit

# set up expected paths & variables 
conduit.IS_INSTALLED =          False
conduit.SHARED_DATA_DIR =       os.path.join(script_path,"data")
conduit.GLADE_FILE =            os.path.join(script_path,"data","conduit.glade")
conduit.SHARED_MODULE_DIR =     os.path.join(script_path,"conduit")
conduit.EXTRA_LIB_DIR =         os.path.join(script_path,"contrib")

# here comes the actual DeltaProvider testing!
import conduit.DeltaProvider as DeltaProvider
import conduit.DataProvider as DataProvider
import conduit.datatypes.Note as Note

class DeltaTest1(DataProvider.TwoWay):
    _name_ = "DeltaTest1"
    _description_ = "Blah blah"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.notes = args[0]
        self.data = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)

        self.data = []

        for n in self.notes:
            note = Note.Note(n)
            note.set_UID(n)
            self.data.append(note)
        
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.data)

    def get(self, index):
        DataProvider.TwoWay.get(self,index)
        return self.data[index]

    def put(self, change, changeOnTopOf):
        DataProvider.TwoWay.put(self,change,changeOnTopOf)

    def finish(self):
        self.data = None

p = DeltaTest1([1,2,3,4,6])
dp = DeltaProvider.DeltaProvider(p)

dp.refresh()
for i in range(0, dp.get_num_items()):
    d = dp.get(i)
    print "%s (%s)" % (d.get_UID(), d.change_type)

dp.finish()

print "Done"
