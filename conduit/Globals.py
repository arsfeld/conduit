"""
Excapsulates those items global to the Conduit process
"""
class Globals:
    def __init__(self):
        #settings is global and initialized early
        self.settings = None

        #to save resources DB, moduleManager and typeConverter are global
        self.moduleManager = None
        self.typeConverter = None
        self.mappingDB = None
        #syncManager provides the single point of cancellation when exiting
        self.syncManager = None

        #the main application
        self.app = None

        #Global cancellation flag
        self.cancelled = False

        #the application main loop
        self.mainloop = None

