"""
Represents a group of conduits

Copyright: John Stowers, 2007
License: GPLv2
"""
from conduit import log,logd,logw, APPVERSION

import traceback
import os
import xml.dom
import xml.dom.ext
import xml.dom.minidom

import gobject

from conduit.Conduit import Conduit
from conduit.Settings import Settings

class SyncSet(gobject.GObject):
    """
    Represents a group of conduits
    """
    __gsignals__ = {
        #Fired when a new instantiatable DP becomes available. It is described via 
        #a wrapper because we do not actually instantiate it till later - to save memory
        "conduit-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    # The ConduitModel that was added
        "conduit-removed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT]),    # The ConduitModel that was removed
        }

    def __init__(self, moduleManager, syncManager, xmlSettingFilePath="settings.xml"):
        gobject.GObject.__init__(self)

        self.moduleManager = moduleManager
        self.syncManager = syncManager
        self.xmlSettingFilePath = xmlSettingFilePath
        self.conduits = []

        self.moduleManager.connect("dataprovider-available", self.on_dataprovider_available_unavailable)
        self.moduleManager.connect("dataprovider-unavailable", self.on_dataprovider_available_unavailable)


        # FIXME: temporary hack - need to let factories know about this factory :-\!
        self.moduleManager.emit("syncset-added", self)

    def on_dataprovider_available_unavailable(self, loader, dpw):
        """
        Removes all PendingWrappers corresponding to dpw and replaces with new dpw instances
        """
        print "AVAIL/UNAVAIL"
        key = dpw.get_key()
        for c in self.get_all_conduits():
            for dp in c.get_dataproviders_by_key(key):
                new = self.moduleManager.get_new_module_instance(key)
                #retain configuration information
                new.set_configuration_xml(dp.get_configuration_xml())
                c.change_dataprovider(
                                    oldDpw=dp,
                                    newDpw=new
                                    )

    def emit(self, *args):
        """
        Override the gobject signal emission so that all signals are emitted 
        from the main loop on an idle handler
        """
        gobject.idle_add(gobject.GObject.emit,self,*args)

    def add_conduit(self, conduit):
        self.conduits.append(conduit)
        self.emit("conduit-added", conduit)

    def remove_conduit(self, conduit):
        self.emit("conduit-removed", conduit)
        self.conduits.remove(conduit)

    def get_all_conduits(self):
        return self.conduits

    def num_conduits(self):
        return len(self.conduits)

    def clear(self):
        for c in self.conduits[:]:
            self.remove_conduit(c)

    def save_to_xml(self):
        """
        Saves the synchronisation settings (icluding all dataproviders and how
        they are connected) to an xml file so that the 'sync set' can
        be restored later
        """
        log("Saving Sync Set to %s" % self.xmlSettingFilePath)
        #Build the application settings xml document
        doc = xml.dom.minidom.Document()
        rootxml = doc.createElement("conduit-application")
        rootxml.setAttribute("version", APPVERSION)
        doc.appendChild(rootxml)
        
        #Store the conduits
        for conduit in self.conduits:
            conduitxml = doc.createElement("conduit")
            conduitxml.setAttribute("uid",conduit.uid)
            conduitxml.setAttribute("twoway",str(conduit.is_two_way()))
            rootxml.appendChild(conduitxml)
            
            #Store the source
            source = conduit.datasource
            if source is not None:
                sourcexml = doc.createElement("datasource")
                sourcexml.setAttribute("key", source.get_key())
                conduitxml.appendChild(sourcexml)
                #Store source settings
                configxml = xml.dom.minidom.parseString(source.get_configuration_xml())
                sourcexml.appendChild(configxml.documentElement)
            
            #Store all sinks
            sinksxml = doc.createElement("datasinks")
            for sink in conduit.datasinks:
                sinkxml = doc.createElement("datasink")
                sinkxml.setAttribute("key", sink.get_key())
                sinksxml.appendChild(sinkxml)
                #Store sink settings
                configxml = xml.dom.minidom.parseString(sink.get_configuration_xml())
                sinkxml.appendChild(configxml.documentElement)
            conduitxml.appendChild(sinksxml)        

        #Save to disk
        try:
            file_object = open(self.xmlSettingFilePath, "w")
            xml.dom.ext.PrettyPrint(doc, file_object)
            file_object.close()        
        except IOError, err:
            logw("Could not save settings to %s (Error: %s)" % (self.xmlSettingFilePath, err.strerror))
        
    def restore_from_xml(self):
        """
        Restores sync settings from the xml file
        """
        log("Restoring Sync Set")
           
        def restore_dataprovider(conduit, wrapperKey, dpxml, trySourceFirst):
            """
            Adds the dataprovider back onto the canvas at the specifed
            location and configures it with the given settings
            
            @returns: The conduit the dataprovider was restored to
            """
            logd("Restoring %s to (source=%s)" % (wrapperKey,trySourceFirst))
            wrapper = self.moduleManager.get_new_module_instance(wrapperKey)
            if wrapper is not None:
                for i in dpxml.childNodes:
                    if i.nodeType == i.ELEMENT_NODE and i.localName == "configuration":
                        wrapper.set_configuration_xml(xmltext=i.toxml())

            conduit.add_dataprovider(wrapper, trySourceFirst)

        #Check the file exists
        if not os.path.isfile(self.xmlSettingFilePath):
            log("%s not present" % self.xmlSettingFilePath)
            return
            
        try:
            #Open                
            doc = xml.dom.minidom.parse(self.xmlSettingFilePath)
            xmlVersion = doc.documentElement.getAttribute("version")
            #And check it is the correct version        
            if xmlVersion != APPVERSION:
                log("%s xml file is incorrect version" % self.xmlSettingFilePath)
                os.remove(self.xmlSettingFilePath)
                return
            
            #Parse...    
            for conds in doc.getElementsByTagName("conduit"):
                print conds.localName
                #create a new conduit
                conduit = Conduit(self.syncManager, conds.getAttribute("uid"))
                self.add_conduit(conduit)

                #restore conduit specific settings
                twoway = Settings._string_to_bool(conds.getAttribute("twoway"))
                if twoway == True:
                    conduit.enable_two_way_sync()

                #each dataprovider
                for i in conds.childNodes:
                    #keep a ref to the dataproider was added to so that we
                    #can apply settings to it at the end
                    #one datasource
                    if i.nodeType == i.ELEMENT_NODE and i.localName == "datasource":
                        key = i.getAttribute("key")
                        #add to canvas
                        if len(key) > 0:
                            restore_dataprovider(conduit, key,i , True)
                    #many datasinks
                    elif i.nodeType == i.ELEMENT_NODE and i.localName == "datasinks":
                        #each datasink
                        for sink in i.childNodes:
                            if sink.nodeType == sink.ELEMENT_NODE and sink.localName == "datasink":
                                key = sink.getAttribute("key")
                                #add to canvas
                                if len(key) > 0:
                                    restore_dataprovider(conduit, key,sink, False)

        except:
            logw("Error parsing %s. Exception:\n%s" % (self.xmlSettingFilePath, traceback.format_exc()))
            os.remove(self.xmlSettingFilePath)

