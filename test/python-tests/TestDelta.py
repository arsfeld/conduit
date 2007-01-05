#common sets up the conduit environment
from common import *

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

if __name__ == '__main__':
    p = DeltaTest1([1,2,3,4,6])
    dp = DeltaProvider.DeltaProvider(p)
    dp.refresh()

    #check some functions
    num_items = dp.get_num_items()
    ok("get_num_items() returns a number = %s" % num_items, type(num_items) == int)
    for i in range(0, dp.get_num_items()):
        d = dp.get(i)
        ok("get() returns != None %s (%s)" % (d.get_UID(), d.change_type), d != None)        

    dp.finish()

