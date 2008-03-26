import re
import os
import signal
import popen2
import logging
log = logging.getLogger("Utils")

class CommandLineConverter:
    def __init__(self):
        self.percentage_match = re.compile('.*')

    def _kill(self, process):
        log.debug("Killing process")
        os.kill(process.pid, signal.SIGKILL)

    def build_command(self, command, **params):
        self.command = command
        
    def calculate_percentage(self, val):
        return float(val)

    def check_cancelled(self):
        return False

    def convert( self, input_filename, output_filename, callback=None,save_output=False):
        command = self.command % (input_filename, output_filename)
        log.debug("Executing %s" % command)

        output = ""
        process = popen2.Popen4(command)
        stdout = process.fromchild
        s = stdout.read(80)
        if save_output:
            output += s
        while s:
            if callback:
                for i in self.percentage_match.finditer(s):
                    val = self.calculate_percentage(i.group(1).strip())
                    callback(val)
            if save_output:
                output += s
            if self.check_cancelled():
                self._kill(process)
            s = stdout.read(80)

        ok = process.wait() == 0
        if save_output:
            return ok, output
        else:
            return ok
