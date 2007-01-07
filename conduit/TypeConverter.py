"""
Holds the TypeConverter class

Copyright: John Stowers, 2006
License: GPLv2
"""

import traceback
from gettext import gettext as _

import logging
import conduit
import conduit.Exceptions as Exceptions

class TypeConverter: 
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
    	
    def __init__ (self, moduleManager):
        """
        Builds the conversion dictionary

        @param dynamic_modules: The dynamically loaded converters
        """

        moduleManager.make_modules_callable("converter")
        self.dynamic_modules = moduleManager.get_modules_by_type("converter")
        #dict of dicts
        self.convertables = {}
        
        for d in self.dynamic_modules:
            conv = getattr(d.module,"conversions", None)
            if conv is not None:
                for c in conv:
                    try:
                        #Conversions are described as fromtype,totype
                        fromtype = c.split(',')[0]
                        totype = c.split(',')[1]
                    
                        #if the from source doesnt yet exist add an inner dict
                        #containing the FROM type and conversion function
                        if not self.convertables.has_key(fromtype):
                            new_conv = {totype:conv[c] }
                            self.convertables[fromtype] = new_conv

                        #Otherwise we already have an inner dict so can go
                        #ahead and insert a new TO type and conversion function
                        else:
                            self.convertables[fromtype][totype] = conv[c]
                    except IndexError:
                        logging.error(  "Conversion dict (%s) wrong format. "\
                                        "Should be fromtype,totype" % c)
                    except KeyError, err:
                        logging.error(  "Could not add conversion function " \
                                        "from %s to %s" % (fromtype,totype))
                        logging.error("KeyError was %s" % err)
                    except Exception:
                        logging.error("Error #341")
                    
    def convert(self, from_type, to_type, data):
        """
        Converts a L{conduit.DataType.DataType} (or derived) of type 
        from_type into to_type and returns that newly converted type
        
        @param from_type: The name of the type converted from
        @type from_type: C{string}
        @param to_type: The name of the type to convert to
        @type to_type: C{string}
        @param data: The DataType to convert
        @type data: L{conduit.DataType.DataType}
        @raise Exceptions.ConversionError: If the conversion fails
        @todo: Make this use conversion_exists first.
        """
        try:
            logging.debug("Converting %s -> %s" % (from_type, to_type))
            return self.convertables[from_type][to_type](data)
        except TypeError, err:
            extra="Could not call conversion function\n%s" % traceback.format_exc()
            raise Exceptions.ConversionError(from_type, to_type, extra)
        except KeyError:
            logging.warn("Conversion from %s -> %s does not exist " % (from_type, to_type))
            logging.warn("Trying conversion from %s -> text & text -> %s" % (from_type, to_type))
            try:
                intermediate = self.convertables[from_type]["text"](data)
                return self.convertables["text"][to_type](intermediate)
            except Exception, err:
                #This is the normal case where the conversion just doesnt exist
                raise Exceptions.ConversionError(from_type, to_type, err)
        except Exception, err:
            extra="Unknown error calling conversion function\n%s" % traceback.format_exc()
            raise Exceptions.ConversionError(from_type, to_type, extra)
            
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
                
    def conversion_exists(self, from_type, to_type, throughTextAllowed=True):
        """
        Checks if a conversion exists 
        
        Conversions through text are allowed if calling this function and
        not specifying the throughTextAllowed parameter
        @todo: Null check self.convertables??
        
        @param from_type: Type to convert from
        @type from_type: C{str}
        @param to_type: Type to convert into
        @type to_type: C{str}                
        @param throughTextAllowed: Are conversions through text allowed?
        @type throughTextAllowed: C{bool}
        """
        if self.convertables.has_key(from_type):
            #from_type exists
            if self.convertables[from_type].has_key(to_type):
                #conversion exists
                return True
            elif self.convertables[from_type].has_key("text") and self.convertables["text"].has_key(to_type):
                #can convert via text
                if throughTextAllowed:
                    return True
                else:
                    return False
            else:
                #to_type doesnt exists
                return False
        else:
            #from_type doesnt exist
            return False
            
    def direct_conversion_exists(self, fromType, toType):
        """
        Checks if a direct conversion exists (conversions through text are 
        not direct allowed)
        
        @param fromType: Type to convert from
        @type fromType: C{str}
        @param toType: Type to convert into
        @type toType: C{str}        
        """
        return self.conversion_exists(fromType, toType, False)
            
