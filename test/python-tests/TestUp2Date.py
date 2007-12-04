#common sets up the conduit environment
from common import *

from conduit.dataproviders.AutoSync import BrokenAutoSync as AutoSync

class Mock(AutoSync):
    def get_changes(self):
        raise NotImplementedError
    def finish(self,aborted,error,conflict):
        pass

a = Mock()
a.handle_added("1")
ok("ADD", len(a.as_added)==1 and len(a.as_modified)==0 and len(a.as_deleted)==0)

a = Mock()
a.handle_modified("1")
ok("MOD", len(a.as_added)==0 and len(a.as_modified)==1 and len(a.as_deleted)==0)

a = Mock()
a.handle_deleted("1")
ok("DEL", len(a.as_added)==0 and len(a.as_modified)==0 and len(a.as_deleted)==1)

# If we get two adds, only one should appear in get_changes!
a = Mock()
a.handle_added("1")
a.handle_added("1")
ok("ADD ADD", len(a.as_added)==1 and len(a.as_modified)==0 and len(a.as_deleted)==0)

# If we get an add and an edit, ignore the edit!
a = Mock()
a.handle_added("1")
a.handle_modified("1")
ok("ADD MOD", len(a.as_added)==1 and len(a.as_modified)==0 and len(a.as_deleted)==0)

# If we get and add and a delete then other side never even needs to see it!
a = Mock()
a.handle_added("1")
a.handle_deleted("1")
ok("ADD DEL", len(a.as_added)==0 and len(a.as_modified)==0 and len(a.as_deleted)==0)

# If we get a mod and an add, ignore the add!
a = Mock()
a.handle_modified("1")
a.handle_added("1")
ok("MOD ADD", len(a.as_added)==0 and len(a.as_modified)==1 and len(a.as_deleted)==0)

# If we get two mods, only one should appear in get_changes!
a = Mock()
a.handle_modified("1")
a.handle_modified("1")
ok("MOD MOD", len(a.as_added)==0 and len(a.as_modified)==1 and len(a.as_deleted)==0)

# If we get a mod and a delete, only delete should appear in get_changes!
a = Mock()
a.handle_modified("1")
a.handle_deleted("1")
ok("MOD DEL", len(a.as_added)==0 and len(a.as_modified)==0 and len(a.as_deleted)==1)

# If we get a del and then add, treat as modified in get_changes!
a = Mock()
a.handle_deleted("1")
a.handle_added("1")
ok("DEL ADD", len(a.as_added)==0 and len(a.as_modified)==1 and len(a.as_deleted)==0)

# If we get a del and then a mod, the universe will fall apart. ignore the mod??
a = Mock()
a.handle_deleted("1")
a.handle_modified("1")
ok("DEL MOD", len(a.as_added)==0 and len(a.as_modified)==0 and len(a.as_deleted)==1)

# If we get two dels, only one should appear in get_changes!
a = Mock()
a.handle_deleted("1")
a.handle_deleted("1")
ok("DEL DEL", len(a.as_added)==0 and len(a.as_modified)==0 and len(a.as_deleted)==1)

finished()

