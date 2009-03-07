# Copyright 2009 - Andrew Stomont <andyjstormont@googlemail.com>
#
# This file is part of GPE-Mail.
#
# GPE-Mail is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# GPE-Mail is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GPE-Mail.  If not, see <http://www.gnu.org/licenses/>.

from os.path import exists
from xml.dom.minidom import parseString

class Settings( object ):
    """
    A class to store/retrieve data to/from an XML file
    """

    def __init__(self, xml_text="<configuration/>"):
        """
        Initializes Settings class
        """
        self.xml_document = parseString(xml_text)

    def __string_to_type__(self, string, desired_type):
        """
        Converts a string into the desired scalar type
        """
        if desired_type == "bool":
            return self.__bool_from_string__(string)
        elif desired_type == "float":
            return float(string)
        elif desired_type == "int":
            return int(string)
        elif desired_type == "str":
            return str(string) # 'just in case'

    def __type_as_string__(self, data_type):
        """
        Returns string name of given data type
        """
        if type(data_type) == list:
            return "list"
        elif type(data_type) == tuple:
            return "tuple"
        elif type(data_type) == dict:
            return "dict"
        elif type(data_type) == int:
            return "int"
        elif type(data_type) == float:
            return "float"
        elif type(data_type) == str:
            return "str"
        elif type(data_type) == bool:
            return "bool"

    def __bool_from_string__(self, string):
        """
        Returns a bool from a string representation
        """
        if string == "True":
            return True
        else:
            return False

    def __getitem__(self, name):
        """
        Called when variable get via subscript interface
        """
        node = self.__get_data_node__(name)
        if node:
            return self.__node_to_data__(node)
        else:
            raise KeyError(name)

    def __setitem__(self, name, value):
        """
        Called when variable set via subscript interface
        """
        newNode = self.__data_to_node__(name, value)
        oldNode = self.__get_data_node__(name)
        if oldNode:
            self.xml_document.documentElement.replaceChild(newNode, oldNode)
        else:
            self.xml_document.documentElement.appendChild(newNode)

    def __delitem__(self, name):
        """
        Deletes item from saved file
        """
        node = self.__get_data_node__(name)
        if node:
            self.xml_document.documentElement.removeChild(node)
        else:
            raise KeyError(name)

    def __contains__(self, name):
        """
        This gets called by the 'in' construct
        """
        node = self.__get_data_node__(name)
        if node:
            return True
        return False

    def __get_data_node__(self, name):
        """
        Returns data node with given name
        """
        for node in self.xml_document.documentElement.childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.nodeName == name:
                return node

    def __iter__(self):
        return self.iteritems()

    def iteritems(self):
        for node in self.xml_document.documentElement.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                yield node.nodeName, self.__node_to_data__(node)

    def __data_to_node__(self, name, data):
        """
        Converts a python data type into an xml node
        """
        node = self.xml_document.createElement(str(name))
        node.setAttribute("type", self.__type_as_string__(data))
        #node.setAttribute("name", str(name))
        if type(data) == dict:
            for (index, value) in data.iteritems():
                node.appendChild( self.__data_to_node__(index, value ))
        elif type(data) == list:
            for (index, value) in enumerate(data):
                node.appendChild(self.__data_to_node__("item", value))
        else:
            node.appendChild(self.xml_document.createTextNode(str(data)))
        return node

    def __node_to_data__(self, node):
        """
        Returns python data from data node
        """
        node_type = node.getAttribute("type")
        if node_type == "dict":
            retval = {}
            for childNode in node.childNodes:
                if childNode.nodeType == node.ELEMENT_NODE:
                    retval[childNode.nodeName] = self.__node_to_data__(childNode)
            return retval
        elif node_type in ("list", "tuple"):
            retval = []
            for childNode in node.childNodes:
                if childNode.nodeType == node.ELEMENT_NODE:
                    #retval.insert(int(childNode.nodeName), self.__node_to_data__(childNode))
                    retval.append(self.__node_to_data__(childNode))
            if node_type == "tuple":
                retval = tuple(retval)
            return retval
        else:
            if len(node.childNodes) > 0:
                return self.__string_to_type__(node.firstChild.data, node_type)
            else:
                return ""

