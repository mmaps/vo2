import os
import sys
import Queue
from importlib import import_module
from multiprocessing import Process

import task
from util import logs


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
                sample = self.process_input(
                    self.work_queue.get(block=True, timeout=self.cfg.get_float("timeouts", "task_wait")))
            except Queue.Empty:
                self.log.error("%s timed out waiting for work input" % self)
                self.stop = True
            else:
                self.handle_sample(sample)

    def import_tool(self, name):
        self.log.debug("%s importing tool: %s" % (self, name))
        try:
            self.tool = import_module(name)
        except ImportError as e:
            self.log.error("Unable to import specified tool %s: %s" % (name, e))
            self.cleanup()

    def process_input(self, sample):
        self.log.debug("%s processing: %s" % (self, sample))
        if not sample:
            self.cleanup()
        return sample

    def handle_sample(self, sample):
        self.log.debug("Handling: %s" % sample)
        tsk = task.Task(self.cfg, self.vm, sample)
        if self.setup_task(tsk):
            self.run_task(tsk)
        self.cleanup_task(tsk)

    def setup_task(self, tsk):
        return tsk.init_task_log()

    def run_task(self, tsk):
        self.tool.run(tsk)

    def cleanup_task(self, tsk):
        self.log.debug("Cleaning up task: %s" % tsk)
        tsk.close_log()

    def cleanup(self):
        self.log.info("%s cleaning up" % self)
        sys.exit(0)

    def __str__(self):
        return "%s-CTRL" % self.vm.name
