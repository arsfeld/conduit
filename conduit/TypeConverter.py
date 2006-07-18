import gobject
import traceback
from gettext import gettext as _

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
                        #I cant work out why in python i cant just go
                        #bla[][] = bla to start the inner dict and 
                        #instead have to do this 
                        
                        #if the from source doesnt yet exist add an inner dict
                        #containing the FROM type and conversion function
                        if not self.convertables.has_key(str(c)):
                            new_conv = { str(d.in_type):conv[c] }
                            self.convertables[str(c)] = new_conv
                        #Otherwise we already have an inner dict so can go
                        #ahead and insert a new TO type and conversion function
                        else:
                            self.convertables[str(c)][str(d.in_type)] = conv[c]
                    except KeyError, err:
                        logging.error("Could not add conversion function from %s to %s" % (c, d.in_type))
                        logging.error("KeyError was %s" % err)
                    except Exception:
                        logging.error("Error #341")
                    
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
            logging.error("Could not call conversion function %s" % err)
            return None
        except KeyError:
            logging.error("Conversion from %s to %s does not exist " % (from_type, to_type))
            return None
        except Exception:
            logging.error("Error #65")
            return None
            
    def get_convertables_descriptive_list(self):
        """
        Returns an array of C{string}s in the form 
        "Convert from BLA to BLA"
        
        Used for display in the GUI and in debugging
        
        @returns: List of descriptive strings
        @rtype: C{string[]}
        """
        CONVERT_FROM_MESSAGE = _("Convert from")
        CONVERT_INTO_MESSAGE = _("into")        
        
        l = []
        for froms in self.convertables:
            for tos in self.convertables[froms]:
                msg = "%s %s %s %s" % ( CONVERT_FROM_MESSAGE,
                                        froms,
                                        CONVERT_INTO_MESSAGE,
                                        tos)
                l.append(msg)
        return l
                
                                        
        
        
    def print_convertables(self):
        """
        Prints a nice textual representation of all types in the system
        and what those can be converted to. 
        """
        for froms in self.convertables:
            for tos in self.convertables[froms]:
                method = self.convertables[froms][tos]
                logging.info("Convert from %s to %s using %s" % (froms, tos, method))
        
