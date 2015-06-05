import os
import sys
from time import strftime, localtime

from util import files

class Task(object):

    def __init__(self, cfg, sample):
        """
        :type cfg: vo2.vcfg.Config
        """
        self.cfg = cfg
        self.vm = None
        self.sample = sample
        self.logdir = ''
        self.logfile = sys.stderr

    def set_vm(self, vm):
        self.vm = vm

    def set_log(self, logdir, logfile):
        self.logdir = logdir
        self.logfile = logfile

    def setup_vm(self):
        self.vm.update_state()
        if self.vm.is_running():
            self.log("Task: Setup Powering off VM")
            self.vm.poweroff()
        if not self.vm.is_saved():
            self.log("Task: Setup Restoring VM")
            self.vm.restore(self.cfg.get("job", "snapshot"))
        return self.vm.start()

    def teardown_vm(self):
        self.log('Task: Powering off %s' % self.vm)
        self.vm.busy = False
        rv = self.vm.poweroff()
        if not rv:
            self.log('Task: Error shutting down %s. Attempting to restore' % self.vm)
            self.vm.poweroff()
            rv = self.vm.restore()
        self.log('Task: shut down %s' % self.vm)
        return rv

    def start_pcap(self, name_suffix=''):
        self.log("Task: PCAP enabled")
        self.vm.stop_sniff()
        pcap_path = os.path.join(self.logdir, '%s%s.pcap' % (self.sample.name, name_suffix))
        self.log("Task: PCAP file: %s" % pcap_path)
        self.vm.set_pcap(pcap_path)
        self.vm.start_sniff()

    def stop_pcap(self):
        if not self.vm.stop_sniff():
            self.log("Task: Unable to stop PCAP")
        if not self.vm.wait_agent():
            self.log("Task: Error waiting for agent response")

    def load_sample(self):
        if not self.sample or self.sample.filetype is files.ERR:
            self.log("Invalid or missing sample")
            return False
        src = self.sample.path
        dst = "%s\\%s" % (self.cfg.get("job", "guestworkingdir"), repr(self.sample))
        self.log("Task: Pushing sample\n\t\tTASK: src %s\n\t\tTASK: dst %s" % (src, dst))
        return self.vm.push(self.cfg.get("job", "user"), src, dst, self.cfg.get("job", "guestworkingdir"))

    def log(self, msg):
        try:
            self.logfile.write("%s: %s\n" % (strftime("%H:%M:%S", localtime()), msg))
        except IOError as err:
            sys.stderr.write("Logging error: %s\n" % err)
        except AttributeError:
            sys.stderr.write(msg)
            sys.stderr.flush()

    def __str__(self):
        string = "Task:"
        try:
            string += "%s,%s" % (self.vm.name, self.sample.name)
        except AttributeError:
            string += "None,None"
        finally:
            return string


