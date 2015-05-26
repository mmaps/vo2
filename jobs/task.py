import os
import sys
import logging
from time import sleep, strftime, localtime

from catalog.samples import Sample
from guests import vbox
from util import files


class Task(object):

    def __init__(self, cfg, vm, sample):
        """
        :type cfg: vo2.vcfg.Config
        """
        self.cfg = cfg
        self.vm = vm
        self.sample = sample
        self.logdir = ''
        self.logfile = sys.stderr
        self.retval = False

    def init_task_log(self):
        self.logdir = self.init_logdir(self.sample.logdir)
        if not self.logdir:
            return False
        logfile = self.open_task_log(self.logdir, self.sample.name, self.vm.name)
        if not logfile:
            return False
        self.logfile = logfile
        return True

    def init_logdir(self, sub_path):
        root_path = self.cfg.get("general", "log_root")
        path = os.path.join(root_path, sub_path)
        if files.make_log_dir(path):
            return path
        else:
            return None

    def open_task_log(self, path, sample, vm):
        logpath = os.path.join(path, "%s.%s.txt" % (sample, vm))
        try:
            logfile = open(logpath, "w")
        except IOError as e:
            self.log("TASK: Error creating task log: %s" % e)
            logfile = None
        return logfile

    def reset_vm(self):
        self.vm.update_state()
        if self.vm.state is vbox.RUNNING:
            self.log("TASK: Setup Powering off VM")
            self.vm.poweroff()
        if self.vm.state is not vbox.SAVED:
            self.log("TASK: Setup Restoring VM")
            self.vm.restore(self.cfg.get("job", "snapshot"))

    def setup_pcap(self, name_suffix=''):
        if self.cfg.get_bool("job", "pcap"):
            self.log("TASK: PCAP enabled")
            self.vm.stop_sniff()
            pcap_path = os.path.join(self.logdir, '%s%s.pcap' % (self.sample.name, name_suffix))
            self.log("TASK: PCAP file: %s" % pcap_path)
            self.vm.set_pcap(pcap_path)

    def start_vm(self):
        if not self.vm.start():
            self.log("TASK: Failed to start VM: %s" % self.vm)
            return False

    def run_sample(self, cmd, execution_time, working_dir):
        self.log("TASK RUN SAMPLE ENTRY")

        if self.cfg.pcap:
            if not self.vm.start_sniff():
                self.log("TASK: Unable to start PCAP")

        self.log("TASK execute: %s" % cmd)
        rv = self.vm.guest_cmd(cmd, execution_time, True, working_dir)

        if self.cfg.pcap:
            if not self.vm.stop_sniff():
                self.log("TASK: Unable to stop PCAP")
            if not self.vm.wait_agent():
                self.log("TASK: Error waiting for agent response")

        rv = self.verify_return(rv)
        self.log("TASK execute return value: %s\n\t\tTASK execute stdout: %s\n\t\tTASK execute stderr: %s" % (
            rv[0], rv[1], rv[2]))

        return rv

    def verify_return(self, rv):
        self.log("TASK Verify Return")
        if not isinstance(rv, list):
            self.log("TASK Unexpected return value: %s" % rv)
            rv = [True, '', rv]
        elif len(rv) is 1:
            rv.extend(['', 'Missing stderr most likely'])
        elif len(rv) is 2:
            rv.extend(['', 'Missing stdout and stderr'])
        return rv

    def get_results(self, src, dst):
        dst = os.path.join(self.logdir, dst)
        self.log("TASK Get results dst: %s" % dst)
        self.vm.pull(self.cfg.copyprogram, self.cfg.user, src, dst)
        return os.path.isfile(dst)

    def teardown_vm(self):
        self.log('TASK: Powering off %s' % self.vm)
        self.vm.busy = False
        rv = self.vm.poweroff()
        if not rv:
            self.log('TASK: Error shutting down %s. Attempting to restore' % self.vm)
            self.vm.poweroff()
            rv = self.vm.restore()
        self.log('TASK: shut down %s' % self.vm)
        return rv

    def load_sample(self):
        if self.sample.filetype is Sample.ERR:
            self.log("TASK: Sample error: %s" % self.sample)
            return False
        src = self.sample.path
        dst = "%s\\%s" % (self.cfg.guestworkingdir, repr(self.sample))
        self.log("TASK: Pushing sample\n\t\tTASK: src %s\n\t\tTASK: dst %s" % (src, dst))
        return self.vm.push(self.cfg.copyprogram, self.cfg.user, src, dst)

    def complete(self):
        try:
            self.vm.release()
        except AttributeError:
            logging.error("Task Complete() failed to release VM obj: %s" % self.vm)

    def close_log(self):
        if self.logfile:
            self.log("-- END LOG --")
            self.logfile.close()

    def log(self, msg):
        try:
            self.logfile.write("[%s] %s\n" % (strftime("%H:%M:%S", localtime()), msg))
        except IOError as err:
            sys.stderr.write("Logging error: %s\n" % err)
        except AttributeError:
            sys.stderr.write(msg)
            sys.stderr.flush()
        else:
            self.logfile.flush()

    def __str__(self):
        try:
            s = "Task\n\tSample: %s\n\tVM: %s\n\tCfg: %s\n" % (self.sample.path, self.vm.name, self.cfg.get("job", "name"))
        except AttributeError:
            s = "Task\n\tVM: %s\n\tCfg: %s\n" % (self.vm.name, self.cfg.get("job", "name"))
        return s
