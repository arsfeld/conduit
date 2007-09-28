"""
Excapsulates those items global to the Conduit process
"""
import conduit.Settings as Settings

class Globals(object):
    def __init__(self):
        #settings is global and initialized early
        self.settings = Settings.Settings()

        #to save resources DB, moduleManager and typeConverter are global
        self.moduleManager = None
        self.typeConverter = None
        self.mappingDB = None
        #syncManager provides the single point of cancellation when exiting
        self.syncManager = None

        #the main application
        self.app = None        

