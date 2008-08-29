"""
Holds the TypeConverter class

Copyright: John Stowers, 2006
License: GPLv2
"""
import traceback
import logging
log = logging.getLogger("TypeConverter")

import conduit.Exceptions as Exceptions
import conduit.utils as Utils

class Converter:
    _module_type_ = "converter"

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
        #dict of dict of conversion functions
        self.convertables = {}

        moduleManager.make_modules_callable("converter")
        dynamic_modules = moduleManager.get_modules_by_type("converter")
        for d in dynamic_modules:
            self._add_converter(d)

    def _add_converter(self, converterWrapper):
            conv = getattr(converterWrapper.module,"conversions", {})
            for c in conv:
                try:
                    #Conversions are described as fromtype,totype
                    fromtype = c.split(',')[0]
                    totype = c.split(',')[1]
                    #if the from source doesnt yet exist add an inner dict
                    #containing the FROM type and conversion function
                    if not self.convertables.has_key(fromtype):
                        self.convertables[fromtype] = {totype:conv[c]}
                    #Otherwise we already have an inner dict so can go
                    #ahead and insert a new TO type and conversion function
                    else:
                        self.convertables[fromtype][totype] = conv[c]
                except IndexError:
                    log.warn("Conversion dict (%s) wrong format. Should be fromtype,totype" % c)
                except KeyError, err:
                    log.warn("Could not add conversion function from %s to %s\n%s" % (fromtype,totype,err))
                except Exception:
                    log.warn("BAD PROGRAMMER")

    def _retain_info_in_conversion(self, fromdata, todata):
        """
        Retains the original datatype properties through a type conversion.
        Properties retained include;
          - gnome-open'able URI
          - modification time
          - original UID
        Call this function from a typeconverter
        """
        if todata == None:
            log.warn("Conversion from %s returned None" % (fromdata))
        else:
            todata.set_mtime(fromdata.get_mtime())
            todata.set_open_URI(fromdata.get_open_URI())
            todata.set_UID(fromdata.get_UID())
        return todata
        
    def _get_conversions(self, from_type, to_type):
        """
        Returns the conversions required fromtype -> totype. Considers if fromtype and/or
        totype are super/subclasses of each other. The args string is always taken from the 
        destination, i.e. the totype.

        Does not check if the conversion actually exists.

        @returns: list of (fromtype, totype, args) tuples
        """
        conversions = []
        args = {}
        fromType = from_type
        toType = to_type

        #remove the args string of present at source
        try:
            fromType = from_type.split("?")[0]
        except ValueError: pass

        #args string is only considered for the destination
        try:
            toType,argString = to_type.split("?")
            args = Utils.decode_conversion_args(argString)
        except ValueError: pass            

        if fromType != toType:
            #check first for and explicit conversion
            if self._conversion_exists(fromType, toType):
                conversions.append( (fromType, toType, args) )
            else:
                froms = fromType.split("/")
                tos = toType.split("/")
                if froms[0] == tos[0]:
                    #same base type, so only convert parent -> child e.g.
                    #file/audio -> file = file -> file
                    #file -> file/audio = file -> file/audio
                    conversions.append( (froms[0],"/".join(tos),args) )
                else:
                    #different base type, e.g.
                    #foo/bar -> bar/baz
                    if len(tos) > 1:
                        #Two conversions are needed, a main type, and a subtype
                        #conversion. remains is any necessary subtype conversion
                        conversions.append( (froms[0], tos[0], {}) )
                        conversions.append( (tos[0],"/".join(tos),args) )
                    else:
                        #Just a main type conversion is needed (remember the args)
                        conversions.append( (froms[0], tos[0], args) )
        else:
            conversions.append( (fromType, toType, args) )

        return conversions

    def _conversion_exists(self, from_type, to_type):
        if self.convertables.has_key(from_type):
            if self.convertables[from_type].has_key(to_type):
                return True
        return False
        
    def _convert(self, conversions, data):
        if data and len(conversions) > 0:
            from_type, to_type, args = conversions[0]
            message = "Converting"
            if from_type == to_type:
                message = "Transcoding"
                #No conversion needed, or module does not supply transcode.
                if args == {} or not self._conversion_exists(from_type, to_type):
                    log.debug("Skipping %s -> %s" % (from_type, to_type))
                    return data

            log.debug("%s %s -> %s (args: %s)" % (message, from_type, to_type, args))
            try:
                #recurse
                return self._convert(
                                conversions[1:],
                                self.convertables[from_type][to_type](data, **args)
                                )
            except Exception:
                log.debug(traceback.format_exc())
                raise Exceptions.ConversionError(from_type, to_type)
        else:
            return data
                        
    def conversion_exists(self, from_type, to_type):
        """
        Checks if all conversion(s) exists to convert from from_type 
        into to_type
        """
        for f,t,a in self._get_conversions(from_type, to_type):
            if f != t and not self._conversion_exists(f,t):
                log.debug("Conversions %s -> %s doesnt exist" % (f,t))
                return False
        return True

    def convert(self, from_type, to_type, data):
        """
        Converts a L{conduit.DataType.DataType} (or derived) of type 
        from_type into to_type and returns that newly converted type. If no
        conversion is needed, the original data is returned.

        @param from_type: The name of the type converted from
        @type from_type: C{string}
        @param to_type: The name of the type to convert to
        @type to_type: C{string}
        @param data: The DataType to convert
        @type data: L{conduit.DataType.DataType}
        """
        conversions = self._get_conversions(from_type, to_type)
        log.debug("Convert %s -> %s using %s" % (from_type, to_type, conversions))

        if self.conversion_exists(from_type, to_type):
            #recursively perform the needed conversions
            newdata = self._convert(conversions, data)
        else:
            raise Exceptions.ConversionDoesntExistError(from_type, to_type)
            
        return self._retain_info_in_conversion(fromdata=data, todata=newdata)

    def get_convertables_list(self):
        """
        Returns a list of 2-tuples specifying conversions (from->to)
        """
        l = []
        for froms in self.convertables:
            for tos in self.convertables[froms]:
                l.append( (froms, tos) )
        return l
                
          
