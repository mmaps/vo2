import os
import sys
import Queue
from importlib import import_module
from multiprocessing import Process

from util import logs, files


class TaskController(Process):

    def __init__(self, cfg, vm, work_queue):
        """
        :type cfg: conf.vcfg.Config
        :type vm: guests.vbox.VirtualMachine
        :type sample_queue: Queue.Queue
        """
        super(TaskController, self).__init__()
        self.cfg = cfg
        self.vm = vm
        self.tool = None
        self.work_queue = work_queue
        self.stop = False
        self.log = logs.init_logging("%s" % self, self.cfg.get("general", "debug"))

    def run(self):
        self.log.info("%s task controller running" % self)
        self.import_tool(self.cfg.get("job", "tool"))
        while not self.stop:
            try:
                tsk = self.process_input(
                    self.work_queue.get(block=True, timeout=self.cfg.get_float("timeouts", "task_wait")))
            except Queue.Empty:
                self.log.error("%s timed out waiting for work input" % self)
                self.stop = True
            else:
                self.handle_task(tsk)

    def import_tool(self, name):
        self.log.debug("%s importing tool: %s" % (self, name))
        try:
            self.tool = import_module(name)
        except ImportError as e:
            self.log.error("Unable to import specified tool %s: %s" % (name, e))
            self.cleanup()

    def process_input(self, tsk):
        self.log.debug("%s processing: %s" % (self, tsk))
        if not tsk:
            self.cleanup()
        return tsk

    def handle_task(self, tsk):
        self.log.debug("Handling: %s" % tsk)
        if self.setup_task(tsk):
            self.run_task(tsk)
        self.cleanup_task(tsk)

    def setup_task(self, tsk):
        tsk.set_vm(self.vm)
        logdir, logfile = self.get_task_log(tsk)
        tsk.set_log(logdir, logfile)
        return tsk.vm and tsk.logdir and tsk.logfile

    def get_task_log(self, tsk):
        logdir = self.init_logdir(tsk.sample.logdir)
        if not logdir:
            return False
        logfile = self.open_task_log(logdir, tsk.sample.name, self.vm.name)
        if not logfile:
            return False
        return logdir, logfile

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

    def run_task(self, tsk):
        self.tool.run(tsk)

    def cleanup_task(self, tsk):
        self.log.debug("Cleaning up task: %s" % tsk)
        tsk.logfile.close()

    def cleanup(self):
        self.log.info("%s cleaning up" % self)
        sys.exit(0)

    def __str__(self):
        return "%s-CTRL" % self.vm.name
