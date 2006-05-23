import sys
import gtk, gobject
import conduit, Utils

class DataProvider:
    """
    Class from which both data sources and dataproviders extend.
    Provides the ability to be displayed onto the canvas
    """
	def __init__(self, iconfile="gtk-file"):
		"""
		Both classes have an iconic represenation which is displayed in
        the treeview and on the canvas
		"""
        self._icon = Utils.load_icon(iconfile)

    #---------- diacanvas.CanvasElement ----------
			
	def deserialize(self, class_name, serialized):
        print "not implemented"
		#try:
		#	match = getattr(sys.modules[self.__module__], class_name)(self, **serialized)
		#	if match.is_valid():
		#		return match
		#except Exception, msg:
		#	print 'Warning:Error while deserializing match:', class_name, serialized, msg
		#return None

    def serialize(self, class_name):
        print "not implemented"
		
	def get_icon(self):
		"""
		Returns a GdkPixbuf hat represents this handler.
		Returns None if there is no associated icon.
		"""
		return self._icon
	

