import os
import logging
log = logging.getLogger("Utils")

class Memstats:
    """
    Memory analysis functions taken from
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/286222
    """

    _proc_status = '/proc/%d/status' % os.getpid()
    _scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
              'KB': 1024.0, 'MB': 1024.0*1024.0}
              
    def __init__(self):
        self.prev = [0.0,0.0,0.0]

    def _VmB(self, VmKey):
        #get pseudo file  /proc/<pid>/status
        try:
            t = open(self._proc_status)
            v = t.read()
            t.close()
        except Exception, err:
            return 0.0  # non-Linux?
        #get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
        i = v.index(VmKey)
        v = v[i:].split(None, 3)  # whitespace
        if len(v) < 3:
            return 0.0  # invalid format?
        #convert Vm value to bytes
        return float(v[1]) * self._scale[v[2]]
        
    def calculate(self):
        VmSize = self._VmB('VmSize:') - self.prev[0]
        VmRSS = self._VmB('VmRSS:') - self.prev [1]
        VmStack = self._VmB('VmStk:') - self.prev [2]
        log.info("Memory Stats: VM=%sMB RSS=%sMB STACK=%sMB" %(
                                    VmSize  / self._scale["MB"],
                                    VmRSS   / self._scale["MB"],
                                    VmStack / self._scale["MB"],
                                    ))
        return VmSize,VmRSS,VmStack 
