import gobject
import traceback

import logging
import conduit

class TypeConverter(gobject.GObject): 
    """
    Maintains a dictionary of dictionaries, indexed by the type converted FROM which
    maps to a list of types that can be converted TO
    
    An example statically constructed conversion dictionary is::
    
        self.convertables = {
                            "from1" : 
                                    {
                                        "to1":from1_to_to1_converter,
                                        "to2":from1_to_to2_converter
                                    },
                            "from2" : 
                                    {
                                        "to3":from2_to_to3_converter,
                                        "to1":from2_to_to1_converter
                                    },
                            "from3" :                                        
                                    {
                                        "to5":from3_to_to5_converter
                                    }
                            }
    
    
    @ivar convertables: The name of the contained module
    @type convertables: C{dict of dicts}, see description 
    in L{conduit.TypeConverter.TypeConverter}
    """
    	
    def __init__ (self, dynamic_modules):
        gobject.GObject.__init__(self)
        
        self.dynamic_modules = dynamic_modules
        #dict of dicts
        self.convertables = {}
        
        for d in self.dynamic_modules:
            conv = getattr(d.module,"conversions", None)
            if conv is not None:
                for c in conv:
                    try:
                        new_conv = { str(d.in_type):conv[c] }
                        self.convertables[str(c)] = new_conv
                    except KeyError, err:
                        print "Error: Could not add conversion function from %s to %s" % (c, d.in_type)
                        print "Error Message: ", err
                    except Exception:
                        print "Error: Error adding conversion function"
                    
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
        try:
            return self.convertables[from_type][to_type](data)
        except TypeError, err:
            print "Error: Could not call conversion function"
            print "Error Message: ", err
            return None
        except KeyError:
            print "Error: Conversion from %s to %s does not exist " % (from_type, to_type)
            return None
        except Exception:
            return None
        
    def print_convertables(self):
        """
        Prints a nice textual representation of all types in the system
        and what those can be converted to. 
        """
        for froms in self.convertables:
            for tos in self.convertables[froms]:
                method = self.convertables[froms][tos]
                print "Convert from %s to %s using %s" % (froms, tos, method)      
        
