import sys
import gtk, gobject
import conduit

class DataSource(conduit.DataProvider.DataProvider):
	def __init__(self, iconfile):
		"""
		Indeed
		"""
		if type(iconfile) == tuple:
			for icon in iconfile:
				self._icon = deskbar.Utils.load_icon(icon)
				if self._icon != None:
					break
		else:
			self._icon = deskbar.Utils.load_icon(iconfile)
			
	def set_priority(self, prio):
		self._priority = prio
		
	def get_priority(self):
		"""
		Returns the global priority (against other handlers) of this handler as int
		"""
		return self._priority
	
	def deserialize(self, class_name, serialized):
		try:
			match = getattr(sys.modules[self.__module__], class_name)(self, **serialized)
			if match.is_valid():
				return match
		except Exception, msg:
			print 'Warning:Error while deserializing match:', class_name, serialized, msg

		return None
		
	def get_icon(self):
		"""
		Returns a GdkPixbuf hat represents this handler.
		Returns None if there is no associated icon.
		"""
		return self._icon
	
	def initialize(self):
		"""
		The initialize of the Handler should not block. 
		Heavy duty tasks such as indexing should be done in this method, it 
		will be called with a low priority in the mainloop.
		
		Handler.initialize() is guarantied to be called before the handler
		is queried.
		
		If an exception is thrown in this method, the module will be ignored and will
		not receive any query.
		"""
		pass
	
	def stop(self):
		"""
		If the handler needs any cleaning up before it is unloaded, do it here.
		
		Handler.stop() is guarantied to be called before the handler is 
		unloaded.
		"""
		pass
		
	def query(self, query):
		"""
		Searches the handler for the given query string.
		Returns a list of
			(string, match object) tuple or
			match object, when the string is the same as the passed one.
		"""
		raise NotImplementedError

	def on_key_press(self, query, shortcut):
		"""
		Called when the user presses a special trigger combination, like alt-foo
		The query text and text press gtk event are passed.
		
		The handler must return None if it didn't handle the key press, or a Match instance if
		it handled the keypress, and the returned match will be executed with the query text
		"""
		return None
		
	def is_async (self):
		"""
		AsyncHandler overwrites this method and returns True.
		It is used to determine whether we should call some async specific methods/signals.
		"""
		return False

class SignallingHandler (Handler, gobject.GObject):
	"""
	This handler is an asynchronous handler using natural glib libraries, like
	libebook, or galago, or twisted.
	"""
	__gsignals__ = {
		"query-ready" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_STRING, gobject.TYPE_PYOBJECT])
	}

	def __init__ (self, iconfile=None):
		Handler.__init__ (self, iconfile)
		gobject.GObject.__init__ (self)
		self.__last_query = None
		self.__start_query_id = 0
		self.__delay = 0

	def set_delay (self, timeout):
		self.__delay = timeout

	def query_async (self, qstring):
		if self.__delay == 0:
			self.__query_async_real (qstring)
			return
		# Check if there is a query delayed, and remove it if so
		if self.__start_query_id != 0:
			gobject.source_remove(self.__start_query_id)

		self.__start_query_id = gobject.timeout_add(self.__delay, self.__query_async_real, qstring) 

	def __query_async_real (self, qstring):
		"""
		When we receive an async call, we first register the most current search string.
		Then we call with a little delay the actual query() method, implemented by the handler.
		"""
		self.__last_query = qstring
		try:
			self.query (qstring)
		except TypeError:
			self.query (qstring, deskbar.DEFAULT_RESULTS_PER_HANDLER)

	def emit_query_ready (self, qstring, matches):
		if qstring == self.__last_query:
			self.emit ("query-ready", qstring, matches)

	def stop_query (self):
		self.__last_query = None
		
	def is_async (self):
		return True
		
if gtk.pygtk_version < (2,8,0):
	gobject.type_register(SignallingHandler)
	
# Here begins the Nastyness
from Queue import Queue
from Queue import Empty
from threading import Thread

class NoArgs :
	pass

class QueryStopped (Exception):
	pass	

class QueryChanged (Exception):
	def __init__ (self, new_query):
		self.new_query = new_query
				
class AsyncHandler (Handler, gobject.GObject):
	"""
	This class can do asynchronous queries. To implement an AsyncHandler just write it
	like you would an ordinary (sync) Handler. Ie. you main concern is to implement a
	query() method.
	
	In doing this you should regularly call check_query_changed() which will restart
	the query if the query string has changed. This method can handle clean up methods
	and timeouts/delays if you want to check for rapidly changing queries.
	
	To return a list of Matches either just return it normally from query(), or use
	emit_query_ready(matches) to emit partial results.
	
	There will at all times only be at maximum one thread per AsyncHandler.
	"""

	__gsignals__ = {
		"query-ready" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_STRING, gobject.TYPE_PYOBJECT]),
	}

	QUERY_PRIORITY = gobject.PRIORITY_DEFAULT_IDLE

	def __init__ (self, iconfile=None):
		Handler.__init__ (self, iconfile)
		gobject.GObject.__init__ (self)
		self.__query_queue = Queue ()
		self.is_running = False
	
	def query_async (self, qstring):
		"""
		This method is the one to be called by the object wanting to start a new query.
		If there's an already running query that one will be cancelled if possible.
		
		Each time there is matches ready there will be a "query-ready" signal emitted
		which will be handled in the main thread. A list of Match objects will be passed
		argument to this signal.
		
		Note: An AsyncHandler may signal on partial results. The thread need not have
		exited because there's a 'query-ready' signal emitted. Read: Don't assume that the
		handler only return Matches one time.
		"""
		if not self.is_running:
			self.is_running = True
			Thread (None, self.__query_async, args=(qstring,)).start ()
			#print "AsyncHandler: Thread created for %s" % self.__class__ # DEBUG
		else:
			self.__query_queue.put (qstring, False)
	
	def stop_query (self):
		"""
		Instructs the handler to stop the query the next time it does check_query_changed().
		"""
		if self.is_running:
			self.__query_queue.put (QueryStopped)
	
	def emit_query_ready (self, qstring, matches):
		"""
		Use this method to emit partial results. matches should be a list of Match objects.
		
		Note: returning a list of Match objects from the query() method automatically
		emits a 'query-ready' signal for this list. 
		"""
		gobject.idle_add (self.__emit_query_ready, qstring, matches)
		
	def check_query_changed (self, clean_up=None, args=NoArgs, timeout=None):
		"""
		Checks if the query has changed. If it has it will execute clean_up(args)
		and raise a QueryChanged exception. DO NOT catch this exception. This should
		only be done by __async_query().
		
		If you pass a timeout argument this call will not return before the query
		has been unchanged for timeout seconds.
		"""
		qstring = None
		try:
			qstring = self.__get_last_query (timeout)
		except QueryStopped:
			if clean_up:
				if args == NoArgs:
					clean_up ()
				else:
					clean_up (args)
			#print "AsyncHandler: Query stopped", self.__class__ # DEBUG
			raise QueryStopped()
		if qstring:
			# There's a query queued
			# cancel the current query.
			if clean_up:
				if args == NoArgs:
					clean_up ()
				else:
					clean_up (args)
			#print "AsyncHandler: Query changed", self.__class__ # DEBUG
			raise QueryChanged (qstring)
		
	def __emit_query_ready (self, qstring, matches):
		"""Idle handler to emit a 'query-ready' signal to the main loop."""
		self.emit ("query-ready", qstring, matches)
		return False

	def __query_async (self, qstring):
		"""
		The magic happens here.
		"""
		try:
			try:
				res = self.query (qstring)
			except TypeError:
				res = self.query (qstring, deskbar.DEFAULT_RESULTS_PER_HANDLER)
				
			if (res and res != []):
				self.emit_query_ready (qstring, res)
			self.is_running = False
			
		except QueryChanged, query_change:
			try:
				self.__query_async (query_change.new_query)
			except QueryStopped:
				self.is_running = False
				#print "AsyncHandler: %s thread terminated." % str(self.__class__) # DEBUG
				
		except QueryStopped:
			self.is_running = False
			#print "AsyncHandler: %s thread terminated." % str(self.__class__) # DEBUG

	def __get_last_query (self, timeout=None):
		"""
		Returns the query to be put on the query queue. We don't wan't to
		do all the intermediate ones... They're obsolete.
		
		If there's a QueryStopped class somewhere in the queue 
		(put there by stop_query()) raise a QueryStopped exeption.
		This exception will be caught by __query_async()
		
		If timeout is passed then wait timeout seconds to see if new queries
		are put on the queue.
		"""
		tmp = None
		last_query = None
		try:
			while True:
				# Get a query without blocking (or only block
				# timeout seconds).
				# The get() call raises an Empty exception
				# if there's no element to get()
				if timeout:
					tmp = self.__query_queue.get (True, timeout)
				else:
					tmp = self.__query_queue.get (False)
				last_query = tmp
				if last_query == QueryStopped:
					raise QueryStopped ()
		except Empty:
			return last_query

	def is_async (self):
		"""Well what do you think?"""
		return True

if gtk.pygtk_version < (2,8,0):
	gobject.type_register(AsyncHandler)
