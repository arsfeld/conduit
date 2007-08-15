import sys, inspect
import AutoSoup

#common sets up the conduit environment
from common import *

# This is the python code 
SimpleTest = """\
#
# DO NOT EDIT, AUTOMATICALLY GENERATED
# 

import sys, thread

from AutoTemplate import *
from AutoSoup import *

try:
    # The dataproviders we are testing
    source = %s().instance(host)
    sink = %s().instance(host)

    # The data sample we are using
    data = %s()
    dataset = data.get()
    datatype = str(data._datatype_)

    # Test local <--> local
    test_full_set(host, source, sink, datatype, dataset)

    if datatype in ("contact", "note"):
        # Test networked <--> local
        newsource = host.networked_dataprovider(source)
        test_full_set(host, newsource, sink, datatype, dataset)
        
        # Test local <--> networked
        newsink = host.networked_dataprovider(sink)
        test_full_set(host, source, newsink, datatype, dataset)

        # Test networked <--> networked
        test_full_set(host, newsource, newsink, datatype, dataset)

except:
    sys.excepthook(*sys.exc_info())
    ok("Unhandled borkage", False)
    thread.interrupt_main()"""

# It's hard to pick sane combinations of dps, so heres a little rules table to help out
# col 1 = weight. in sync folder <--> contact we need to use contact objects over file objects.
# col 2 = a function to call to get some data.
# As a bonus, reject combinations where col 1 is same (e.g. contact <--> event)
rules = {}
for name in dir(AutoSoup):
    cls = getattr(AutoSoup, name)
    if name[:7] == "objset_" and inspect.isclass(cls):
        rules[cls._datatype_] = (cls._weight_, cls._name_)

targets = []
combinations = []

# Cludge to gather all the dataprovider initialisers
for name in dir(AutoSoup):
    cls = getattr(AutoSoup, name)
    if name[:5] == "prep_" and inspect.isclass(cls):    
        targets.append( cls() )

for source in targets:
    for sink in targets:
        if source != sink:
            in_type1 = source._datatype_
            in_type2 = sink._datatype_

            if in_type1 == in_type2:
                combinations.append( (source, sink, in_type1, rules[in_type1][1]) )
            elif rules[in_type1][0] > rules[in_type2][0]:
                combinations.append( (source, sink, in_type1, rules[in_type1][1]) )
            elif rules[in_type2][0] > rules[in_type1][0]:
                combinations.append( (source, sink, in_type2, rules[in_type2][1]) )

for source, sink, datatype, dataset in combinations:
    f = open('test/python-tests/TestAuto_%s_%s.py' % (source, sink), 'w')
    f.write(SimpleTest % (source, sink, dataset))

