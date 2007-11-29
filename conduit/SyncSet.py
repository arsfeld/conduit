"""
Represents a group of conduits

Copyright: John Stowers, 2007
License: GPLv2
"""
import traceback
import os
import xml.dom.minidom
import gobject
import logging
log = logging.getLogger("SyncSet")

import conduit
import conduit.Conduit as Conduit
import conduit.Settings as Settings

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
        
    def _unitialize_dataproviders(self, cond):
        for dp in cond.get_all_dataproviders():
            if dp.module:
                dp.module.uninitialize()
                
    def _restore_dataprovider(self, cond, wrapperKey, dpName, dpxml, trySourceFirst):
        """
        Adds the dataprovider back onto the canvas at the specifed
        location and configures it with the given settings
        """
        log.debug("Restoring %s to (source=%s)" % (wrapperKey,trySourceFirst))
        wrapper = self.moduleManager.get_new_module_instance(wrapperKey)
        wrapper.set_name(dpName)
        if wrapper is not None:
            for i in dpxml.childNodes:
                if i.nodeType == i.ELEMENT_NODE and i.localName == "configuration":
                    wrapper.set_configuration_xml(xmltext=i.toxml())
        cond.add_dataprovider(wrapper, trySourceFirst)

    def on_dataprovider_available_unavailable(self, loader, dpw):
        """
        Removes all PendingWrappers corresponding to dpw and replaces with new dpw instances
        """
        key = dpw.get_key()
        for c in self.get_all_conduits():
            for dp in c.get_dataproviders_by_key(key):
                new = self.moduleManager.get_new_module_instance(key)
                #retain configuration information
                new.set_configuration_xml(dp.get_configuration_xml())
                new.set_name(dp.get_name())
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

    def add_conduit(self, cond):
        self.conduits.append(cond)
        self.emit("conduit-added", cond)

    def remove_conduit(self, cond):
        self.emit("conduit-removed", cond)
        self._unitialize_dataproviders(cond)
        self.conduits.remove(cond)

    def get_all_conduits(self):
        return self.conduits

    def get_conduit(self, index):
        return self.conduits[index]

    def index (self, conduit):
        return self.conduits.index(conduit)        

    def num_conduits(self):
        return len(self.conduits)

    def clear(self):
        for c in self.conduits[:]:
            self.remove_conduit(c)

    def save_to_xml(self, xmlSettingFilePath=None):
        """
        Saves the synchronisation settings (icluding all dataproviders and how
        they are connected) to an xml file so that the 'sync set' can
        be restored later
        """
        if xmlSettingFilePath == None:
            xmlSettingFilePath = self.xmlSettingFilePath
        log.info("Saving Sync Set to %s" % self.xmlSettingFilePath)

        #Build the application settings xml document
        doc = xml.dom.minidom.Document()
        rootxml = doc.createElement("conduit-application")
        rootxml.setAttribute("version", conduit.APPVERSION)
        doc.appendChild(rootxml)
        
        #Store the conduits
        for cond in self.conduits:
            conduitxml = doc.createElement("conduit")
            conduitxml.setAttribute("uid",cond.uid)
            conduitxml.setAttribute("twoway",str(cond.is_two_way()))
            rootxml.appendChild(conduitxml)
            
            #Store the source
            source = cond.datasource
            if source is not None:
                sourcexml = doc.createElement("datasource")
                sourcexml.setAttribute("key", source.get_key())
                sourcexml.setAttribute("name", source.get_name())
                conduitxml.appendChild(sourcexml)
                #Store source settings
                configxml = xml.dom.minidom.parseString(source.get_configuration_xml())
                sourcexml.appendChild(configxml.documentElement)
            
            #Store all sinks
            sinksxml = doc.createElement("datasinks")
            for sink in cond.datasinks:
                sinkxml = doc.createElement("datasink")
                sinkxml.setAttribute("key", sink.get_key())
                sinkxml.setAttribute("name", sink.get_name())
                sinksxml.appendChild(sinkxml)
                #Store sink settings
                configxml = xml.dom.minidom.parseString(sink.get_configuration_xml())
                sinkxml.appendChild(configxml.documentElement)
            conduitxml.appendChild(sinksxml)        

        #Save to disk
        try:
            file_object = open(xmlSettingFilePath, "w")
            file_object.write(doc.toxml())
            #file_object.write(doc.toprettyxml())
            file_object.close()        
        except IOError, err:
            log.warn("Could not save settings to %s (Error: %s)" % (xmlSettingFilePath, err.strerror))
        
    def restore_from_xml(self, xmlSettingFilePath=None):
        """
        Restores sync settings from the xml file
        """
        if xmlSettingFilePath == None:
            xmlSettingFilePath = self.xmlSettingFilePath
        log.info("Restoring Sync Set from %s" % xmlSettingFilePath)
           
        #Check the file exists
        if not os.path.isfile(xmlSettingFilePath):
            log.info("%s not present" % xmlSettingFilePath)
            return
            
        try:
            #Open                
            doc = xml.dom.minidom.parse(xmlSettingFilePath)
            xmlVersion = doc.documentElement.getAttribute("version")
            #And check it is the correct version        
            if xmlVersion != conduit.APPVERSION:
                log.info("%s xml file is incorrect version" % xmlSettingFilePath)
                os.remove(xmlSettingFilePath)
                return
            
            #Parse...    
            for conds in doc.getElementsByTagName("conduit"):
                #create a new conduit
                cond = Conduit.Conduit(self.syncManager, conds.getAttribute("uid"))
                self.add_conduit(cond)

                #restore conduit specific settings
                twoway = Settings.string_to_bool(conds.getAttribute("twoway"))
                if twoway == True:
                    cond.enable_two_way_sync()

                #each dataprovider
                for i in conds.childNodes:
                    #keep a ref to the dataproider was added to so that we
                    #can apply settings to it at the end
                    #one datasource
                    if i.nodeType == i.ELEMENT_NODE and i.localName == "datasource":
                        key = i.getAttribute("key")
                        name = i.getAttribute("name")
                        #add to canvas
                        if len(key) > 0:
                            self._restore_dataprovider(cond, key, name, i, True)
                    #many datasinks
                    elif i.nodeType == i.ELEMENT_NODE and i.localName == "datasinks":
                        #each datasink
                        for sink in i.childNodes:
                            if sink.nodeType == sink.ELEMENT_NODE and sink.localName == "datasink":
                                key = sink.getAttribute("key")
                                name = sink.getAttribute("name")
                                #add to canvas
                                if len(key) > 0:
                                    self._restore_dataprovider(cond, key, name, sink, False)

        except:
            log.warn("Error parsing %s. Exception:\n%s" % (xmlSettingFilePath, traceback.format_exc()))
            os.remove(xmlSettingFilePath)

    def quit(self):
        """
        Calls unitialize on all dataproviders
        """
        for c in self.conduits:
            self._unitialize_dataproviders(c)

