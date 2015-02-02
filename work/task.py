import os
import sys
import logging
from time import sleep, strftime, localtime

from catalog.samples import Sample
from guests import vbox


class Task(object):
    def __init__(self, cfg, vm, name='', path=''):
        """
        :type cfg: vo2.vcfg.Config
        :type vm: vo2.guests.vbox.VirtualMachine
        :param cfg:
        :return:
        """
        self.cfg = cfg
        self.vm = vm
        self.logfile = None
        self.retval = False
        self.sample = Sample(name, path)
        self.rootlogdir = os.path.join(cfg.log, cfg.name)
        self.logdir = os.path.join(self.rootlogdir, self.sample.name)
        self.errors = []

    def init(self):
        mask = os.umask(0007)
        try:
            os.mkdir(self.logdir, 0770)
        except OSError:
            logging.error("TASK unable to create log directory: %s" % self.logdir)
            return False
        os.umask(mask)

        try:
            logpath = os.path.join(self.logdir, "%s.%s.log" % (self.sample.name, self.vm.name))
        except AttributeError:
            logpath = os.path.join(self.logdir, "%s.log" % self.vm.name)

        try:
            self.logfile = open(logpath, 'w')
        except IOError:
            sys.stderr.write("Unable to create log file: %s\n" % logpath)
            return False
        else:
            self.log("-- BEGIN LOG --\nTASK VM: %s" % self.vm.name)
            if self.vm.update_state() is vbox.RUNNING:
                self.vm.poweroff()
            self.log("TASK Initial VM State: %s" % self.vm)
            self.log("TASK Sample: %s" % self.sample)
            return True

    def setup_vm(self, suffix=''):
        self.log("TASK: Setup VM: %s" % self.vm)
        self.vm.busy = True
        self.vm.update_state()

        self.log("TASK: Updated VM: %s" % self.vm)

        if self.vm.state is vbox.RUNNING:
            self.log("TASK: Setupt Powering off VM")
            self.vm.poweroff()

        if self.vm.state is not vbox.SAVED:
            self.log("TASK: Setup Restoring VM")
            self.vm.restore(self.cfg.snapshot)

        self.log("TASK: Starting, %s" % self.vm)
        rv = self.vm.start()
        if not rv:
            self.log("TASK: Failed to start VM: %s" % self.vm)
            return False

        self.log("TASK: Started, %s" % self.vm)

        if self.sample.type is not Sample.NEW:
            rv = self.load_sample()

        if self.cfg.pcap:
            self.log("TASK: PCAP enabled")
            self.vm.stop_sniff()
            pcap_path = os.path.join(self.logdir, '%s%s.pcap' % (self.sample.name, suffix))
            self.log("TASK: PCAP file: %s" % pcap_path)
            self.vm.set_pcap(pcap_path)

        return rv

    def run_sample(self, cmd, execution_time, working_dir):
        self.log("TASK RUN SAMPLE ENTRY")

        if self.cfg.pcap:
            if not self.vm.start_sniff():
                self.log("TASK: Unable to start PCAP")

        self.log("TASK execute: %s" % cmd)
        rv = self.vm.guest.execute(cmd, execution_time, True, working_dir)

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
        self.vm.winscp_pull(src, dst)
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
        if self.sample.type is Sample.ERR:
            self.log("TASK: Sample error: %s" % self.sample)
            return False
        src = self.sample.path
        dst = "%s\\%s" % (self.cfg.guestworkingdir, repr(self.sample))
        self.log("TASK: Pushing sample\n\t\tTASK: src %s\n\t\tTASK: dst %s" % (src, dst))
        return self.vm.winscp_push(src, dst)

    def complete(self):
        try:
            self.vm.release()
        except AttributeError:
            logging.error("Task Complete() failed to release VM obj: %s" % self.vm)

    def close_log(self):
        if self.logfile:
            for e in self.errors:
                self.logfile.write(e)
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
            s = "Task\n\tSample: %s\n\tVM: %s\n\tCfg: %s\n" % (self.sample.path, self.vm.name, self.cfg.name)
        except AttributeError:
            s = "Task\n\tVM: %s\n\tCfg: %s\n" % (self.vm.name, self.cfg.name)
        return s
