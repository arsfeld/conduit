import gobject
import time
import traceback

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions

class SyncManager(object): 
    """
    Given a dictionary of relationships this class synchronizes
    the relevant sinks and sources
    """
    def __init__ (self, typeConverter):
        #Dictionary of conduits and their status
        self.conduits = {}
        self.typeConverter = typeConverter
        pass
        
    def add_conduit(self, conduit):
        #Add conduit to dictionary if not present
        #if conduit not in self.conduits:
        #    self.conduits[conduit] = conduit.get_status()
        pass

    def initialize_conduit(self, conduit):
        #If we do not 
        pass
        

    def remove_conduit(self, conduit):
        pass
        
    def sync_conduit(self, conduit):
        logging.info("Synchronizing Conduit %s" % conduit)
        
        datasource = conduit.datasource
        datasinks = conduit.datasinks

        sourceData = datasource.module.get()
        for sink in datasinks:
            logging.debug("Synchronizing from %s to %s" % (datasource.name, sink.name))
            for data in sourceData:
                logging.debug("Source data type = %s, Sink accepts %s" % (datasource.out_type, sink.in_type))
                if datasource.out_type != sink.in_type:
                    logging.debug("Conversion Required")
                    data = self.typeConverter.convert(datasource.out_type, sink.in_type, data)
                
                sink.module.put(data)
                    
        
class SyncWorker:
    """
    j
    """
    def __init__(self, typeConverter, conduit):
        """
        Test
        """
        self.typeConverter = typeConverter
        self.source = conduit.datasource
        self.sinks = conduit.datasinks
        self.state = 0

    def run(self, startState=None):
        """
        Takes the conduit through the init->get,put,get,put->done 
        steps, setting its status at the appropriate time and performing
        nicely in the case of errors.
        
        Oh yeah its also threaded so it shouldnt block the gui, and shouldnt
        eat babies.
        
        @todo: Should this be its own inner class which throws some signals 
        when a step is passed. Then a whole bunch of these could be handled
        by the syncmanager
        @todo: Glib 2.10 is threadsafe so aparently set_status() sending signals
        will hopefully not cause Snakes on a Plane. I hope. 
        """
        finished = False
        numOKSinks = 0
        while not finished:
            sourcestatus = self.source.module.get_status()        
            logging.debug("Syncworker State %s" % self.state)
            #Init state
            if self.state is 0:
                #Initialize the source
                if sourcestatus is DataProvider.STATUS_NONE:
                    logging.debug("Init Source")
                    try:
                        self.source.module.set_status(DataProvider.STATUS_INIT)
                        #Thread
                        self.source.module.initialize()
                        self.source.module.set_status(DataProvider.STATUS_DONE_INIT_OK)
                    except Exceptions.InitializeError:
                        self.source.module.set_status(DataProvider.STATUS_DONE_INIT_ERROR)
                        #Let the calling thread know we blew it
                        raise Exceptions.StopSync
                #Init all the sinks. At least one must init successfully
                for sink in self.sinks:
                    sinkstatus = sink.module.get_status()                        
                    if sinkstatus is DataProvider.STATUS_NONE:
                        logging.debug("Init Sink %s" % sink.name)                    
                        try:
                            sink.module.set_status(DataProvider.STATUS_INIT)
                            sink.module.initialize()
                            sink.module.set_status(DataProvider.STATUS_DONE_INIT_OK)
                            numOKSinks += 1
                        except Exceptions.InitializeError:
                            sink.module.set_status(DataProvider.STATUS_DONE_INIT_ERROR)
                            numOKSinks -= 1
                #Need to have at least one successfully inited sink            
                if numOKSinks > 0:
                    #Go to sink state
                    self.state = 1
                else:
                    #go home
                    self.finished = True
            #synchronize state
            elif self.state is 1:
                #try and get the source data iterator
                try:
                    self.source.module.set_status(DataProvider.STATUS_SYNC)
                    sourceData = self.source.module.get()
                #if the source cannot return an iterator then its over    
                except Exceptions.SyncronizeFatalError:
                    self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                    #Cannot continue with no source data                    
                    raise Exceptions.StopSync
                #if we dont know what happened then thats also bad programming
                except Exception, err:                        
                    self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                    logging.warn("UNKNOWN EXCEPTION CAUGHT GETTING SOURCE ITERATOR: %s" % err)
                    traceback.print_exc()
                    #Cannot continue with no source data
                    raise Exceptions.StopSync           
                    
                #OK if we have got this far then we have source data to sync the sinks with             
                for sink in self.sinks:
                    sinkErrorFree = True
                    #only sync with those sinks that init'd OK
                    if sink.module.get_status() is DataProvider.STATUS_DONE_INIT_OK:
                        #Start the sync
                        logging.debug("Synchronizing from %s to %s" % (self.source.name, sink.name))
                        #FIXME how do I check that its iteratable first????
                        for data in sourceData:
                            logging.debug("Source data type = %s, Sink accepts %s" % (self.source.out_type, sink.in_type))
                            try:
                                if self.source.out_type != sink.in_type:
                                    logging.debug("Conversion Required")
                                    data = self.typeConverter.convert(self.source.out_type, sink.in_type, data)
                                #Finally after all the schenigans try an put the data                                
                                sink.module.put(data)
                            #Catch errors from a failed convert
                            except Exceptions.ConversionError, err:
                                #Not fatal, move along
                                logging.warn("Error converting %s" % err)
                                sinkErrorFree = False
                            except Exceptions.SynchronizeConflictError:
                                #FIXME. I imagine that implementing this is a bit of work!
                                logging.warn("Sync Conflict")                            
                            except Exceptions.SyncronizeError:
                                #non fatal, move along
                                logging.warn("NON FATAL SYNC ERROR")                     
                                sinkErrorFree = False                                   
                            except Exceptions.SyncronizeFatalError:
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                logging.warn("FATAL SYNC ERROR")            
                                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)                             
                                #Fatal, go home       
                                raise Exceptions.StopSync                                                    
                            except Exception, err:                        
                                #Bad programmer
                                sink.module.set_status(DataProvider.STATUS_DONE_SYNC_ERROR)
                                logging.warn("UNKNOWN EXCEPTION CAUGHT PUTTING DATA")
                                traceback.print_exc()
                                raise Exceptions.StopSync
                        
                        if sinkErrorFree:
                            #tell the gui if the sync was ok
                            sink.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)

                #Done go to next state
                self.state = 3
            #Done successfully go home without raising exception
            elif self.state is 3:
                finished = True
                #Tell the GUI
                self.source.module.set_status(DataProvider.STATUS_DONE_SYNC_OK)
        
class GIdleThread(object):
    """
    This is a pseudo-"thread" for use with the GTK+ main loop.

    This class does act a bit like a thread, all code is executed in
    the callers thread though. The provided function should be a generator
    (or iterator).

    It can be started with start(). While the "thread" is running is_alive()
    can be called to see if it's alive. wait([timeout]) will wait till the
    generator is finished, or timeout seconds.
    
    If an exception is raised from within the generator, it is stored in
    the error property. Execution of the generator is finished.

    Note that this routine runs in the current thread, so there is no need
    for nasty locking schemes.    __gsignals__ = { 'status-changed': (gobject.SIGNAL_RUN_FIRST, 
                                        gobject.TYPE_NONE,      #return type
                                        (gobject.TYPE_INT,)     #argument
                                        )}

    Example (runs a counter through the GLib main loop routine)::
        >>> def counter(max): for x in xrange(max): yield x
        >>> t = GIdleThread(counter(123))
        >>> t.start()
        >>> while gen.is_alive():
        ...     main.iteration(False)
    """

    def __init__(self, generator):
        assert hasattr(generator, 'next'), 'The generator should be an iterator'
        self._generator = generator
        self._idle_id = 0
        self._error = None

    def start(self, priority=gobject.PRIORITY_LOW):
        """
        Start the generator. Default priority is low, so screen updates
        will be allowed to happen.
        """
        idle_id = gobject.idle_add(self.__generator_executer,
                                   priority=priority)
        self._idle_id = idle_id
        return idle_id

    def wait(self, timeout=0):
        """
        Wait until the corouine is finished or return after timeout seconds.
        This is achieved by running the GTK+ main loop.
        """
        clock = time.clock
        start_time = clock()
        main = gobject.main_context_default()
        while self.is_alive():
            main.iteration(False)
            if timeout and (clock() - start_time >= timeout):
                return

    def interrupt(self):
        """
        Force the generator to stop running.
        """
        if self.is_alive():
            gobject.source_remove(self._idle_id)
            self._idle_id = 0

    def is_alive(self):
        """
        Returns True if the generator is still running.
        """
        return self._idle_id != 0

    error = property(lambda self: self._error,
                     doc="Return a possible exception that had occured "\
                         "during execution of the generator")

    def __generator_executer(self):
        try:
            result = self._generator.next()
            return True
        except StopIteration:
            self._idle_id = 0
            return False
        except Exception, e:
            self._error = e
            traceback.print_exc()
            self._idle_id = 0
            return False

