"""
GConf Export - Utility to export XML, behaves like 
'gconftool-2 --dump /gconf/path > xml' 
Copyright (c) 2006 Peter Moberg <moberg.peter@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

On Debian systems, the complete text of the GNU General Public
License can be found in /usr/share/common-licenses/GPL file.

Modified for use in Conduit by John Stowers

"""

from xml.dom import minidom
import gconf
import types

class GConfExport:
    """
    Allow us to export from gconf to XML
    """
    def __init__(self, client):
        self.client = client
        self.indentStep = "  "

    """
    Returns the get function for a value
    """
    def printEntry(self, key, value, indent):
        
        #If there is an unset value, return empty string
        if (value == None):
            return ""

        try:
            if (value.type == gconf.VALUE_INVALID):
                raise "Invalid value in gconf"
                return ""

            elif (value.type == gconf.VALUE_STRING):
                return self.__getDataValXml("string", self.client.get_string(key), indent)

            elif (value.type == gconf.VALUE_INT):
                return self.__getDataValXml("int", str(self.client.get_int( key )), indent)

            elif (value.type == gconf.VALUE_FLOAT):
                return self.__getDataValXml("float", str(self.client.get_float(key)), indent)

            elif (value.type == gconf.VALUE_BOOL):
                return self.__getDataValXml("bool", str(self.client.get_bool(key)), indent)

            elif (value.type == gconf.VALUE_LIST):
                return self.__getListValXml( value, key, indent ) 

            elif (value.type == gconf.VALUE_SCHEMA):
                raise "Can not export schema, not implemented"
            elif (value.type == gconf.VALUE_PAIR):
                raise "Can not export pair, not implemented"
            else:
                return ""
        except Exception, e:
            #print ""
            print "ERROR in printEntry: "
            print key
            print e
            #print ""
            return ""

    def __getDataValXml(self, type, data, indent):
        """
        Converts a data value to XML
        """
        space = self.__indentSpace(indent)
        space2 = self.__indentSpace(indent+1)
        if (type == "bool"):
            data = data.lower()
        elif (type == "string"):
            data = data.replace('<', '&lt;').replace('>','&gt;')
            
        return ( space + "<value>\n" + space2 + "<" + type + ">" + data + "</" + type + ">\n" +space + "</value>\n")

    def __getListValXml(self, value, key, indent):
        """
        Converts a list of values into XML
        """
        xml = ""
        strType = ""
        listType = value.get_list_type()
        list = []
    
        if (listType == gconf.VALUE_STRING):
            strType = "string"
            list = self.client.get_list(key, gconf.VALUE_STRING)
        elif (listType == gconf.VALUE_INT):
            strType = "int"
            list = self.client.get_list(key, gconf.VALUE_INT)
        elif (listType == gconf.VALUE_FLOAT):
            strType = "float"
            list = self.client.get_list(key, gconf.VALUE_FLOAT)
        elif (listType == gconf.VALUE_BOOL):
            strType = "bool"
            list = self.client.get_list(key, gconf.VALUE_BOOL)

        xml += self.__indentSpace(indent) + "<list type=\"" + strType + "\">\n"
        try:
            for item in list:
                if type(item) == types.StringType:
                    output = item.replace('<', '&lt;').replace('>','&gt;')
                else:
                    output = str(item)
                xml += self.__indentSpace(indent+1) + "<value>\n" + self.__indentSpace(indent+2) +"<" + strType + ">" + output + "</" + strType + ">\n" + self.__indentSpace(indent+1) + "</value>\n"

            xml += self.__indentSpace(indent) + "</list>\n"
        except Exception, e:
            print "__getListValXml:"
            print e
        return xml
                

    def __parseTree(self, path, indent):
        xml = ""
        entries = self.client.all_entries(path)

        for entry in entries:
            key = entry.get_key()
            #print "key: " + key
            try:
                value = entry.get_value()
                xml += self.__indentSpace(indent) + "<entry>\n"
                xml += self.__indentSpace(indent+1) + "<key>" + key + "</key>\n"
                xml += self.printEntry( key, entry.get_value(), indent+2 )
                xml += self.__indentSpace(indent) + "</entry>\n"
            except Exception, e:
                print "__parseTree:"
                print e

        dirs = self.client.all_dirs(path)
        for dir in dirs:
            xml += self.__parseTree(dir, indent)

        return xml


    def exportDir(self, path, indent):
        """
        Recursively exports a GConf dir to XML
        """
        xml = self.__indentSpace(indent) + "<entrylist base=\"" + path + "\">\n"
        xml += self.__parseTree(path, indent+1)        
        xml += self.__indentSpace(indent) + "</entrylist>\n"

        return xml

    def exportKey(self, key, indent):
        """
        Exports a single key to XML
        """
        xml = self.__indentSpace(indent) + "<entrylist base=\"" + key[0:key.rfind('/')] + "\">\n"
        xml += self.__indentSpace(indent+1) + "<entry>\n"
        xml += self.__indentSpace(indent+2) + "<key>" + key + "</key>\n"

        value = self.client.get(key)
        xml += self.printEntry(key, value, indent+3)        

        xml += self.__indentSpace(indent+1) + "</entry>\n"
        xml += self.__indentSpace(indent) + "</entrylist>\n"
        return xml
    
    def export(self, dirs, singleKeys):
        """
        Exports all dirs in 'dirs' and keys in 'singleKeys' to XML. 
        This XML is compatible with gconftool-2
        """
        xml = "<gconfentryfile>\n"

            
        for key in singleKeys:
            xml += self.exportKey(key, 2)
            
        for dir in dirs:
            xml += self.exportDir(dir, 2)

        xml += "</gconfentryfile>\n"
        return xml

    def __indentSpace(self, depth):
        """
        Return correct indentation width
        """
        space = ""
        for i in range(depth):
            space += self.indentStep
        return space

class GConfImport:
    """
    Imports an xml file with gconf values to GConf
    """
    def __init__(self, client=None):
        if (client == None):
            self.client = gconf.client_get_default()
        else:    
            self.client = client

        self.changeSet = None

    def importXml(self, xml, unsetDirs=None):
        """
        Load data from XML and load it into GConf
        """
        
        if unsetDirs == None:
            import config
            unsetDirs = config.defaultDumpDirs
            #unsetDirs = ["/apps/panel"]

        #FIXME: Why isn't recursive unset available in ChangeSet?"""
        #for key in config.defaultDumpKeys:
        #    print "Unsetting key: " + key
        #    self.client.unset(key)
        
        #self.client.unset("/apps/panel/general/applet_id_list")
        self.client.set_list("/apps/panel/general/applet_id_list", gconf.VALUE_STRING, [])

        self.client.unset("/apps/panel/general/applet_id_list")
        self.client.set_list("/apps/panel/general/applet_id_list", gconf.VALUE_STRING, [])
        
        self.client.unset("/apps/panel/general/toplevel_id_list")

        for dir in unsetDirs:
            #print "Unsetting dir: " + dir
            self.client.recursive_unset(dir, 0)
            
        # For now, we will not be using ChangeSet, it simply doesn't work
        # as it should
        
        #changeSet = gconf.ChangeSet()
        changeSet = None
        xmlDoc = minidom.parseString(xml)
        entryList = xmlDoc.getElementsByTagName("entrylist")

        for entryListItem in entryList:
            self.handleEntryList( entryListItem, changeSet )
            
        # Commit the changes
        #print "changeSet to commit:"
        #print changeSet
        #print ""
        #self.client.commit_change_set(changeSet, True)

        # Not pretty at all... but the panel doesn't seem to update correctly otherwise
        #import os
        #import time
        #time.sleep(1)
        #print "Restarting gnome-panel"
        #os.system("killall gnome-panel")


    def getText(self, nodelist):
        """
        Returns a string containing the text of a xml node
        """
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

    def handleEntryList(self, entryList, changeSet):
        """
        Handles a list of entries
        """
        entries = entryList.getElementsByTagName("entry")
        for entry in entries:
            self.handleEntry(entry, changeSet)

    def handleEntry(self, entry, changeSet):
        """
        Handles one <entry>
        """
        key = self.getText((entry.getElementsByTagName("key")[0]).childNodes)
        list = entry.getElementsByTagName("list")

        if (len(list) > 0):
            self.handleList(list[0],key, changeSet)
        else:
            self.handleValues(entry.getElementsByTagName("value"), key, changeSet)

    def handleList(self, list, key, changeSet):
        """
        Inserts list values into GConf
        """
        #print key
        values = (list.getElementsByTagName("value"))
        type = list.getAttribute("type")
        
        list = []
        setType = gconf.VALUE_INVALID
        for value in values:
            if (type == "string"):
                #val = gconf.Value(gconf.VALUE_STRING)
                #val.set_string(str(self.getListValue(value)))
                val = str(self.getListValue(value))
                list.append(val)
                setType = gconf.VALUE_STRING
            elif (type == "int"):
                list.append( int(self.getListValue(value)))
                setType = gconf.VALUE_INT
            elif (type == "bool"):
                list.append( bool(self.getListValue(value)))
                setType = gconf.VALUE_BOOL
            elif (type == "float"):
                list.append( float(self.getListValue(value)))
                setType = gconf.VALUE_FLOAT

#        if (setType != gconf.VALUE_INVALID):
        #print "list: " + key + " (type: " + type + ")"
        #print list

#        if (len(list) > 0):
        #self.client.unset(key)
        self.client.set_list(key, setType, list)
        #self.client.set_list("/apps/panel/general/toplevel_id_list", gconf.VALUE_STRING, ['bottom_panel_screen0', 'top_panel_screen0'])

        #changeSet.set_list(key, setType, list)
        
        #print "changeSet:"
        #print changeSet
        #print ""

        #except Exception, e:
        #    print "Error importing list:"
        #    print e
            
    
    def getListValue(self, value):
        """
        Return the value of a list item
        """
        intValues = value.getElementsByTagName("int")
        stringValues = value.getElementsByTagName("string")
        boolValues = value.getElementsByTagName("bool")
        floatValues = value.getElementsByTagName("float")

        if (len(intValues) > 0 ):
            return int(self.getText(intValues[0].childNodes))

        elif (len(stringValues) > 0 ):
            return str(self.getText(stringValues[0].childNodes))

        elif (len(boolValues) > 0 ):
            return bool(self.getText(boolValues[0].childNodes))

        elif (len(floatValues) > 0 ):
            return float(self.getText(floatValues[0].childNodes))

    def handleValues(self, values, key, changeSet):
        """
        Inserts values into GConf
        """
        for value in values:
            intValues = value.getElementsByTagName("int")
            stringValues = value.getElementsByTagName("string")
            boolValues = value.getElementsByTagName("bool")
            floatValues = value.getElementsByTagName("float")

            if (len(intValues) > 0 ):
                data = self.getText(intValues[0].childNodes)
                #changeSet.set_int( key, int(data) )
                self.client.set_int( key, int(data) )

            elif (len(stringValues) > 0 ):
                data = self.getText(stringValues[0].childNodes)
                #changeSet.set_string( key, str(data) )
                self.client.set_string( key, str(data) )

            elif (len(boolValues) > 0 ):
                data = self.getText(boolValues[0].childNodes)

                if (data == "true"):
                    #changeSet.set_bool( key, True )
                    self.client.set_bool( key, True )
                elif (data == "false"):
                    #changeSet.set_bool( key, False )
                    self.client.set_bool( key, False )

            elif (len(floatValues) > 0 ):
                data = self.getText(floatValues[0].childNodes)
                #changeSet.set_float( key, float(data) )
                self.client.set_float( key, float(data) )

