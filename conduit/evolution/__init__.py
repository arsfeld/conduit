try:
    from _evolution import *
except ImportError:
    #Autotools hack to import the lib from the hidden .libs directory
    import os, sys
    currentdir = os.path.abspath(os.path.dirname(__file__))
    libdir = os.path.join(currentdir,".libs")
    if os.path.isfile(os.path.join(libdir,"_evolution.so")):
        sys.path.insert(0, libdir)
        from _evolution import *
    else:
        print "PLEASE BUILD CONDUIT TO GET EVOLUTION SUPPORT"
        raise ImportError
