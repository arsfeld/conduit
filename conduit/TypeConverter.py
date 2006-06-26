import gobject

class TypeConverter(gobject.GObject): 
    """
    Maintains a dictionary, indexed by the type converted FROM which
    maps to a list of types that can be converted TO
    
    An example statically constructed conversion dictionary is::
    
            self.convertables = {
                            "from1" : 
                                [ 
                                    {"to1":"from1_to_to1_converter"},
                                    {"to2":"from1_to_to2_converter"}
                                ],
                            "from2" : 
                                [ 
                                    {"to3":"from2_to_to3_converter"},
                                    {"to1":"from2_to_to1_converter"}
                                ],
                            "from3" :                                        
                                [
                                    {"to5":"from3_to_to5_converter"}
                                ]
                            }
    
    
    @ivar convertables: The name of the contained module
    @type convertables: C{dict}, see description 
    in L{conduit.TypeConverter.TypeConverter}
    """
    	
    def __init__ (self):
        gobject.GObject.__init__(self)
        
        self.dynamic_modules = []
        self.convertables = {
                            "from1" : 
                                [ 
                                    {"to1":"from1_to_to1_converter"},
                                    {"to2":"from1_to_to2_converter"}
                                ],
                            "from2" : 
                                [ 
                                    {"to3":"from2_to_to3_converter"},
                                    {"to1":"from2_to_to1_converter"}
                                ],
                            "from3" :                                        
                                [
                                    {"to5":"from3_to_to5_converter"}
                                ]
                            }
            
    def convert(self, from_type, to_type, data):
        """
        Converts a L{conduit.DataType.DataType} of type from_type into
        to_type and returns that newly converted type
        
        @param from_type: The name of the type converted from
        @type from_type: C{string}
        @param to_type: The name of the type to convert to
        @type to_type: C{string}
        @param data: The DataType to convert
        @type data: L{conduit.DataType.DataType}
        """
        return None
        
    def print_convertables(self):
        """
        Prints a nice textual representation of all types in the system
        and what those can be converted to. 
        """
        for froms in self.convertables:
            #print "froms ", froms
            for convs in self.convertables[froms]:
                #print "tos ", tos
                for tos in convs:
                    method = convs[tos]
                    #print "tos using", tos[using]
                    print "Convert from %s to %s using %s" % (froms, tos, method)
                        
    def _add_dynamic_type(self, dynamic_module):
        """
        Adds a dynamic type to the dictionary of convertable types.
        """
        return None
        
        
