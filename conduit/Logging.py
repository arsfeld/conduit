import os
import logging
import conduit

# Custom logger class with multiple destinations
class ConduitLogger(logging.Logger):
    FORMAT = "[%(name)-20s][%(levelname)-7s] %(message)s (%(filename)s:%(lineno)d)"
    LOG_FILE_HANDLER = None
    def __init__(self, name):
        try:
            level = getattr(logging,os.environ.get('CONDUIT_LOGLEVEL','DEBUG'))
        except AttributeError:
            level = logging.DEBUG
        logging.Logger.__init__(self, name, level)
        
        #Add two handlers, a stderr one, and a file one
        formatter = logging.Formatter(ConduitLogger.FORMAT)
        
        #create the single file appending handler
        if ConduitLogger.LOG_FILE_HANDLER == None:
            filename = os.path.join(conduit.USER_DIR,'conduit.log')
            ConduitLogger.LOG_FILE_HANDLER = logging.FileHandler(filename,'w')
            ConduitLogger.LOG_FILE_HANDLER.setFormatter(formatter)

        console = logging.StreamHandler()
        console.setFormatter(formatter)
        
        self.addHandler(ConduitLogger.LOG_FILE_HANDLER)
        self.addHandler(console)
        return
logging.setLoggerClass(ConduitLogger)
