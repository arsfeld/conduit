"""
Holds the TypeConverter class

Copyright: John Stowers, 2006
License: GPLv2
"""

import traceback

from conduit import log,logd,logw
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils

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
                        logw("Conversion dict (%s) wrong format. Should be fromtype,totype" % c)
                    except KeyError, err:
                        logw("Could not add conversion function from %s to %s\n%s" % (fromtype,totype,err))
                    except Exception:
                        logw("BAD PROGRAMMER")

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
            logw("Conversion from %s returned None" % (fromdata))
        else:
            todata.set_mtime(fromdata.get_mtime())
            todata.set_open_URI(fromdata.get_open_URI())
            todata.set_UID(fromdata.get_UID())
        return todata

    def _get_conversion(self, from_type, to_type):
        """
        Returns the conversion required fromtype -> totype. Considers if fromtype and/or
        totype are super/subclasses of each other. The args string is always taken from the 
        destination, i.e. the totype.

        Does not check if the conversion actually exists.

        @returns: fromtype, totype, args
        """
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
            froms = fromType.split("/")
            tos = toType.split("/")
            
            #same base type (e.g. file -> file/audio or vice-versa)
            if froms[0] == tos[0]:
                #one is parent class of the other
                if len(froms) != len(tos):
                    #file/audio -> file = file -> file
                    if len(froms) > len(tos):
                        fromType = froms[0]
                        toType = tos[0]

        return fromType, toType, args

    def _conversion_exists(self, from_type, to_type):
        """
        Checks if a conversion exists 
        @param from_type: Type to convert from
        @type from_type: C{str}
        @param to_type: Type to convert into
        @type to_type: C{str}                
        """
        from_type, to_type, args = self._get_conversion(from_type, to_type)

        if self.convertables.has_key(from_type):
            #from_type exists
            if self.convertables[from_type].has_key(to_type):
                return True
            else:
                return False
        else:
            return False

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
        from_type, to_type, args = self._get_conversion(from_type, to_type)

        conversionExists = self._conversion_exists(from_type, to_type)
        #print "------------------ %s -> %s (args: %s) (exists: %s)" % (from_type, to_type, args, conversionExists)

        #if fromtype and totype differ only through args, then check if that
        #datatype has a transcode function (a convert function whose in and
        #out types are the same)
        if from_type == to_type:
            if args == {}:
                return data
            elif conversionExists == True:
                try:
                    logd("Transcoding %s (args: %s)" % (from_type, args))
                    to = self.convertables[from_type][to_type](data, **args)
                    return self._retain_info_in_conversion(fromdata=data, todata=to)
                except Exception, err:
                    extra="Error calling conversion/transcode function\n%s" % traceback.format_exc()
                    raise Exceptions.ConversionError(from_type, to_type, extra)
            else:
                return data
        #perform the conversion
        elif conversionExists == True:
            try:
                logd("Converting %s -> %s (args: %s)" % (from_type, to_type, args))
                to = self.convertables[from_type][to_type](data, **args)
                return self._retain_info_in_conversion(fromdata=data, todata=to)
            except Exception, err:
                extra="Error calling conversion function\n%s" % traceback.format_exc()
                raise Exceptions.ConversionError(from_type, to_type, extra)
        else:
            logw("Conversion from %s -> %s does not exist " % (from_type, to_type))
            raise Exceptions.ConversionDoesntExistError(from_type, to_type)

    def get_convertables_list(self):
        """
        Returns a list of 2-tuples specifying conversions (from->to)
        """
        l = []
        for froms in self.convertables:
            for tos in self.convertables[froms]:
                l.append( (froms, tos) )
        return l
                
          
